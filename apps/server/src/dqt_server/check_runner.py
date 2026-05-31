"""CheckRunner -- connects to warehouse sources, runs dqt checks,
and persists results to Postgres so the API can serve them without hitting
the warehouse on every request.
"""
from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy import select, update as sa_update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from dqt_server.db.engine import AsyncSessionLocal
from dqt_server.models.core import CheckRun, ColumnCheck, Dataset, Incident, Source

log = structlog.get_logger(__name__)

# null_fraction thresholds
_FAIL_THRESHOLD = 0.10
_WARN_THRESHOLD = 0.02


@dataclass
class ColumnCheckResult:
    column: str
    null_fraction: float
    null_count: int
    total: int
    verdict: str  # pass/warn/fail
    message: str


@dataclass
class TableCheckResult:
    table: str
    schema_name: str
    source_id: str
    row_count: int
    column_count: int
    col_names: list[str]
    col_types: list[str]
    checks: list[ColumnCheckResult]
    status: str  # pass/warn/fail
    error: str | None = None


def _bq_credentials_from_json(json_str: str):
    """Build Google credentials from either a service-account or authorized_user JSON."""
    import json as _json
    info = _json.loads(json_str)
    cred_type = info.get("type", "")
    scopes = ["https://www.googleapis.com/auth/cloud-platform"]
    if cred_type == "service_account":
        from google.oauth2 import service_account
        return service_account.Credentials.from_service_account_info(info, scopes=scopes)
    if cred_type == "authorized_user":
        from google.oauth2.credentials import Credentials
        creds = Credentials(
            token=None,
            refresh_token=info["refresh_token"],
            token_uri="https://oauth2.googleapis.com/token",
            client_id=info["client_id"],
            client_secret=info["client_secret"],
        )
        quota_project = info.get("quota_project_id")
        if quota_project:
            creds = creds.with_quota_project(quota_project)
        return creds
    raise ValueError(
        f"Unsupported credentials type '{cred_type}'. "
        "Paste a service account JSON key or application default credentials."
    )


def _bq_credentials_from_password(password: str | None):
    """Resolve BQ credentials from the stored password field.

    Empty/None → Application Default Credentials (ADC).
    Non-empty  → service-account / authorized_user JSON string.
    Returns (credentials, project_id_or_None).
    """
    if not password:
        import google.auth
        creds, project = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        return creds, project
    return _bq_credentials_from_json(password), _bq_project_from_json(password)


def _bq_project_from_json(json_str: str) -> str | None:
    """Extract the GCP project ID from a credentials JSON string, or None."""
    try:
        import json as _json
        info = _json.loads(json_str)
        return info.get("quota_project_id") or info.get("project_id")
    except Exception:
        return None


def _make_adapter(source: Source) -> Any:
    """Create warehouse adapter from Source credentials."""
    engine_lc = source.engine.lower()
    if engine_lc == "clickhouse":
        from dqt.adapters.clickhouse.adapter import ClickHouseAdapter
        from dqt.adapters.clickhouse.config import ClickHouseConfig
        # Prefer Railway internal URL for ClickHouse if host matches public URL
        host = source.host
        internal = os.environ.get("CLICKHOUSE_INTERNAL_URL")
        if internal and os.environ.get("CLICKHOUSE_URL", "") == host:
            host = internal
        cfg = ClickHouseConfig(
            host=host, port=source.port, database=source.db_name,
            username=source.username or "default",
            password=source.password or "",
            secure=source.secure,
        )
        return ClickHouseAdapter(**cfg.to_client_kwargs())
    elif engine_lc == "postgres":
        from dqt.adapters.postgres.adapter import PostgresAdapter
        pw = source.password or ""
        user = source.username or "postgres"
        conn_str = f"postgresql+psycopg2://{user}:{pw}@{source.host}:{source.port}/{source.db_name}"
        return PostgresAdapter(conn_str)
    elif engine_lc == "bigquery":
        from dqt.adapters.bigquery.adapter import BigQueryAdapter
        creds, inferred_project = _bq_credentials_from_password(source.password)
        project = source.host or inferred_project or ""
        return BigQueryAdapter(project=project, credentials=creds)
    else:
        raise ValueError(f"Unsupported engine for refresh: {source.engine}")


def _default_schema_for_source(source: Source) -> str:
    """Return the primary schema name to use when listing tables for a source."""
    engine_lc = source.engine.lower()
    if engine_lc == "clickhouse":
        return source.db_name or "default"
    if engine_lc == "bigquery":
        return source.db_name or ""  # dataset name; empty = scan all
    return "public"


def _list_tables_for_source_sync(source: Source) -> list[dict]:
    """List all tables available in a source warehouse."""
    try:
        adapter = _make_adapter(source)
        schema = _default_schema_for_source(source)
        try:
            schemas = adapter.list_schemas()
            if schemas and schema not in schemas:
                schema = schemas[0]
        except Exception:
            pass
        tables = adapter.list_tables(schema)
        return [{"schema": schema, "name": t} for t in sorted(tables)]
    except Exception as exc:
        log.error("list_tables_failed", source_id=source.id, error=str(exc))
        return []


def _check_table_sync(adapter: Any, schema: str, table: str, source_id: str) -> TableCheckResult:
    """Run null fraction checks for all columns in one warehouse query."""
    try:
        cols = adapter.describe_columns(schema, table)
        col_names = [c.name for c in cols]
        col_types = [c.data_type for c in cols]

        if not col_names:
            return TableCheckResult(
                table=table, schema_name=schema, source_id=source_id,
                row_count=0, column_count=0, col_names=[], col_types=[], checks=[],
                status="unknown",
            )

        exprs = ["COUNT(*) AS __total"]
        for i, col in enumerate(col_names):
            exprs.append(f"countIf(isNull(`{col}`)) AS _n{i}")
        sql = f"SELECT {', '.join(exprs)} FROM `{schema}`.`{table}`"

        result = adapter._client.query(sql)
        row = result.result_rows[0]
        total = int(row[0] or 0)

        checks: list[ColumnCheckResult] = []
        for i, col in enumerate(col_names):
            null_count = int(row[i + 1] or 0)
            frac = null_count / total if total > 0 else 0.0
            verdict = (
                "fail" if frac > _FAIL_THRESHOLD else
                "warn" if frac > _WARN_THRESHOLD else
                "pass"
            )
            checks.append(ColumnCheckResult(
                column=col,
                null_fraction=frac,
                null_count=null_count,
                total=total,
                verdict=verdict,
                message=f"{null_count:,}/{total:,} rows NULL ({frac:.1%})",
            ))

        table_status = (
            "fail" if any(c.verdict == "fail" for c in checks) else
            "warn" if any(c.verdict == "warn" for c in checks) else
            "pass"
        )
        log.info("table_checked", table=table, rows=total, status=table_status)
        return TableCheckResult(
            table=table, schema_name=schema, source_id=source_id,
            row_count=total, column_count=len(col_names), col_names=col_names,
            col_types=col_types, checks=checks, status=table_status,
        )

    except Exception as exc:
        log.error("table_check_failed", table=table, error=str(exc))
        return TableCheckResult(
            table=table, schema_name=schema, source_id=source_id,
            row_count=0, column_count=0, col_names=[], col_types=[], checks=[],
            status="fail", error=str(exc),
        )


def _run_user_checks_sync(
    adapter: Any, schema: str, table: str, col_checks: list[dict]
) -> list[dict]:
    """Run user-defined detectors. Aggregate detectors push SQL to the warehouse;
    sample-based detectors operate on a local sample."""
    import pandas as pd
    from dqt.algorithms._registry import registry
    from dqt.algorithms._base import BaseAggregateDetector

    # Normalize: dataset_id encodes "schema.table"; split when schema is missing.
    if not schema and "." in table:
        schema, table = table.split(".", 1)

    results: list[dict] = []
    # Loaded lazily — only needed for sample-based detectors.
    full_df: pd.DataFrame | None = None
    sample_failed = False

    for cc in col_checks:
        if not cc.get("enabled", True):
            log.debug("check_skipped_disabled", column=cc.get("column_name"), slug=cc.get("detector_slug"))
            continue
        column = cc["column_name"]
        slug = cc["detector_slug"]
        params = cc["params"] or {}

        try:
            detector_cls = registry.get(slug)
        except KeyError:
            log.warning("unknown_detector", slug=slug)
            results.append({
                "column": column, "detector_slug": slug,
                "score": 0.0, "verdict": "error",
                "plain_english": f"Unknown detector: '{slug}'",
                "details": {"error": f"Detector slug '{slug}' is not registered"},
            })
            continue

        # Strip verdict-threshold keys — they configure scoring, not the constructor.
        constructor_params = {k: v for k, v in params.items() if k not in {"warn_threshold", "fail_threshold"}}
        try:
            detector = detector_cls(**constructor_params)
        except Exception as exc:
            log.error("user_detector_init_failed", slug=slug, column=column, error=str(exc))
            results.append({
                "column": column, "detector_slug": slug,
                "score": 0.0, "verdict": "error",
                "plain_english": f"Check misconfigured: {exc}",
                "details": {"error": str(exc)},
            })
            continue

        dialect = getattr(adapter, "sql_dialect", "ansi")
        try:
            if isinstance(detector, BaseAggregateDetector):
                agg_exprs = detector.get_aggregations(column, dialect)
                agg_result = adapter.aggregate(schema, table, agg_exprs)
                det_result = detector.score(pd.DataFrame([agg_result]), {})
            elif hasattr(detector, "get_sample_filters"):
                # Time-windowed detector: fetch reference and current windows separately.
                ref_where, curr_where = detector.get_sample_filters()
                try:
                    ref_df = adapter.sample(schema, table, n=1000, where=ref_where)
                    curr_df = adapter.sample(schema, table, n=1000, where=curr_where)
                except Exception as exc:
                    log.error("windowed_sample_failed", table=table, column=column, error=str(exc))
                    results.append({
                        "column": column, "detector_slug": slug,
                        "score": 0.0, "verdict": "error",
                        "plain_english": f"Windowed sample failed: {exc}",
                        "details": {"error": str(exc)},
                    })
                    continue
                if column not in ref_df.columns or column not in curr_df.columns:
                    log.warning("column_not_found_in_window", table=table, column=column,
                                available=list(ref_df.columns))
                    results.append({
                        "column": column, "detector_slug": slug,
                        "score": 0.0, "verdict": "error",
                        "plain_english": f"Column '{column}' not found in windowed sample",
                        "details": {"error": "column_not_in_sample",
                                    "available_columns": list(ref_df.columns)},
                    })
                    continue
                ref_col = ref_df[[column]].dropna()
                curr_col = curr_df[[column]].dropna()
                if len(ref_col) < 10 or len(curr_col) < 10:
                    results.append({
                        "column": column, "detector_slug": slug,
                        "score": 0.0, "verdict": "error",
                        "plain_english": f"Not enough data to run check (ref={len(ref_col)} rows, curr={len(curr_col)} rows, need ≥10 each)",
                        "details": {"error": "insufficient_data", "ref_rows": len(ref_col), "curr_rows": len(curr_col)},
                    })
                    continue
                state = detector.fit(ref_col)
                det_result = detector.score(curr_col, state)
            else:
                # schema_change needs metadata, not row data
                if slug == "schema_change":
                    try:
                        cols_meta = adapter.describe_columns(schema, table)
                        schema_df = pd.DataFrame([
                            {"col_name": c.name, "data_type": c.data_type} for c in cols_meta
                        ])
                    except Exception as exc:
                        log.error("describe_columns_failed", table=table, error=str(exc))
                        results.append({
                            "column": column, "detector_slug": slug,
                            "score": 0.0, "verdict": "error",
                            "plain_english": f"Could not retrieve schema: {exc}",
                            "details": {"error": str(exc)},
                        })
                        continue
                    if len(schema_df) < 1:
                        results.append({
                            "column": column, "detector_slug": slug,
                            "score": 0.0, "verdict": "error",
                            "plain_english": "Schema has no columns",
                            "details": {"error": "empty_schema"},
                        })
                        continue
                    state = detector.fit(schema_df)
                    det_result = detector.score(schema_df, state)
                    verdict = det_result.verdict.value if hasattr(det_result.verdict, "value") else str(det_result.verdict)
                    results.append({
                        "column": column, "detector_slug": slug,
                        "score": float(det_result.score), "verdict": verdict,
                        "plain_english": det_result.plain_english, "details": det_result.details or {},
                    })
                    continue

                if not sample_failed and full_df is None:
                    try:
                        full_df = adapter.sample(schema, table, n=2000)
                    except Exception as exc:
                        log.error("sample_table_failed", table=table, error=str(exc))
                        sample_failed = True
                if sample_failed:
                    results.append({
                        "column": column, "detector_slug": slug,
                        "score": 0.0, "verdict": "error",
                        "plain_english": "Could not sample table data",
                        "details": {"error": "sample_failed"},
                    })
                    continue

                # Table-level detectors use column "(table)" and need the full DataFrame
                if column == "(table)":
                    col_df = full_df  # type: ignore[assignment]
                    if len(col_df) < 20:  # type: ignore[arg-type]
                        results.append({
                            "column": column, "detector_slug": slug,
                            "score": 0.0, "verdict": "error",
                            "plain_english": f"Not enough data ({len(col_df)} rows, need ≥20)",  # type: ignore[arg-type]
                            "details": {"error": "insufficient_data", "row_count": len(col_df)},  # type: ignore[arg-type]
                        })
                        continue
                else:
                    if column not in full_df.columns:  # type: ignore[union-attr]
                        log.warning("column_not_found", table=table, column=column)
                        results.append({
                            "column": column, "detector_slug": slug,
                            "score": 0.0, "verdict": "error",
                            "plain_english": f"Column '{column}' not found in table sample",
                            "details": {"error": "column_not_in_sample"},
                        })
                        continue
                    col_df = full_df[[column]].dropna()  # type: ignore[index]
                    if len(col_df) < 20:
                        results.append({
                            "column": column, "detector_slug": slug,
                            "score": 0.0, "verdict": "error",
                            "plain_english": f"Not enough data to run check ({len(col_df)} non-null rows, need ≥20)",
                            "details": {"error": "insufficient_data", "row_count": len(col_df)},
                        })
                        continue

                mid = len(col_df) // 2
                state = detector.fit(col_df.iloc[:mid])
                det_result = detector.score(col_df.iloc[mid:], state)

            verdict = det_result.verdict.value if hasattr(det_result.verdict, "value") else str(det_result.verdict)
            results.append({
                "column": column,
                "detector_slug": slug,
                "score": float(det_result.score),
                "verdict": verdict,
                "plain_english": det_result.plain_english,
                "details": det_result.details or {},
            })
        except Exception as exc:
            log.error("user_detector_failed", slug=slug, column=column, error=str(exc))
            results.append({
                "column": column, "detector_slug": slug,
                "score": 0.0, "verdict": "error",
                "plain_english": f"Check failed: {exc}",
                "details": {"error": str(exc)},
            })

    return results


class CheckRunner:
    def __init__(self) -> None:
        self._refreshing = False

    # ------------------------------------------------------------------
    # Async public interface
    # ------------------------------------------------------------------

    async def refresh(self) -> None:
        """Run all warehouse checks across all sources and persist results to Postgres."""
        if self._refreshing:
            log.warning("refresh_already_running")
            return
        self._refreshing = True
        log.info("refresh_started")
        try:
            await self._do_refresh()
        finally:
            self._refreshing = False
        log.info("refresh_done")

    async def run_single(self, check_id: str) -> dict:
        """Run one check by its column_checks.id and return the result dict."""
        if AsyncSessionLocal is None:
            return {"error": "no_db"}

        loop = asyncio.get_event_loop()
        now = datetime.now(timezone.utc)

        async with AsyncSessionLocal() as db:
            cc = await db.get(ColumnCheck, check_id)
            if cc is None:
                return {"error": "check_not_found"}
            dataset = await db.get(Dataset, cc.dataset_id)
            if dataset is None:
                return {"error": "dataset_not_found"}
            source = await db.get(Source, dataset.source_id)
            if source is None:
                return {"error": "source_not_found"}

        try:
            adapter = await loop.run_in_executor(None, _make_adapter, source)
            # Prefer the dataset's own schema_name; fall back to source default.
            schema = dataset.schema_name or _default_schema_for_source(source)
        except Exception as exc:
            log.error("run_single_adapter_failed", check_id=check_id, error=str(exc))
            return {"error": str(exc)}

        # dataset_id is "schema.table"; extract just the table name for the adapter call.
        table_name = cc.dataset_id.rsplit(".", 1)[-1]
        col_check = {
            "column_name": cc.column_name,
            "detector_slug": cc.detector_slug,
            "params": cc.params,
            "enabled": cc.enabled,
        }
        try:
            results = await loop.run_in_executor(
                None, _run_user_checks_sync, adapter, schema, table_name, [col_check]
            )
        except Exception as exc:
            log.error("run_single_executor_failed", check_id=check_id, error=str(exc))
            return {"error": f"executor_error: {exc}"}
        if not results:
            log.error("run_single_empty_results", check_id=check_id, schema=schema, table=table_name)
            return {"error": "no_result"}

        await self._persist_user_check_results(cc.dataset_id, results, now)
        log.info("run_single_done", check_id=check_id, verdict=results[0]["verdict"])
        return {"check_id": check_id, "ran_at": now.isoformat(), **results[0]}

    async def _do_refresh(self) -> None:
        if AsyncSessionLocal is None:
            log.warning("no_db_skipping_refresh")
            return

        loop = asyncio.get_event_loop()
        now = datetime.now(timezone.utc)

        async with AsyncSessionLocal() as db:
            src_result = await db.execute(select(Source))
            all_sources = src_result.scalars().all()

        if not all_sources:
            log.info("no_sources_to_refresh")
            return

        for source in all_sources:
            async with AsyncSessionLocal() as db:
                ds_result = await db.execute(
                    select(Dataset).where(Dataset.source_id == source.id)
                )
                db_datasets = ds_result.scalars().all()

            if not db_datasets:
                continue

            watched = [d.id for d in db_datasets]

            async with AsyncSessionLocal() as db:
                cc_result = await db.execute(
                    select(ColumnCheck).where(ColumnCheck.dataset_id.in_(watched))
                )
                all_col_checks = cc_result.scalars().all()

            col_checks_by_dataset: dict[str, list[dict]] = {}
            for cc in all_col_checks:
                col_checks_by_dataset.setdefault(cc.dataset_id, []).append({
                    "column_name": cc.column_name,
                    "detector_slug": cc.detector_slug,
                    "params": cc.params,
                    "enabled": cc.enabled,
                })

            try:
                adapter = await loop.run_in_executor(None, _make_adapter, source)
                schema = _default_schema_for_source(source)
            except Exception as exc:
                log.error("adapter_creation_failed", source_id=source.id, error=str(exc))
                continue

            all_ok = True
            is_clickhouse = source.engine.lower() == "clickhouse"
            for table in watched:
                if is_clickhouse:
                    result = await loop.run_in_executor(
                        None, _check_table_sync, adapter, schema, table, source.id
                    )
                    if result.status == "fail":
                        all_ok = False
                    await self._persist_table_result(result, now)

                user_checks = col_checks_by_dataset.get(table, [])
                if user_checks:
                    user_results = await loop.run_in_executor(
                        None, _run_user_checks_sync, adapter, schema, table, user_checks
                    )
                    # Fetch row count for non-ClickHouse sources (ClickHouse gets it via _persist_table_result)
                    row_count: int | None = None
                    if not is_clickhouse:
                        try:
                            from dqt.adapters._protocol import AggExpr
                            # Same normalisation as _run_user_checks_sync
                            _schema, _table = schema, table
                            if not _schema and "." in _table:
                                _schema, _table = _table.split(".", 1)
                            count_result = await loop.run_in_executor(
                                None, adapter.aggregate, _schema, _table,
                                [AggExpr("COUNT(*)", "__total")]
                            )
                            row_count = int(count_result.get("__total") or 0)
                        except Exception as exc:
                            log.warning("row_count_failed", table=table, error=str(exc))
                    await self._persist_user_check_results(table, user_results, now, row_count=row_count)

            async with AsyncSessionLocal() as db:
                src = await db.get(Source, source.id)
                if src:
                    src.status = "pass" if all_ok else "warn"
                    src.last_synced_at = now
                    await db.commit()

    async def _persist_table_result(self, result: TableCheckResult, now: datetime) -> None:
        if AsyncSessionLocal is None:
            return

        async with AsyncSessionLocal() as db:
            stmt = pg_insert(Dataset).values(
                id=result.table,
                source_id=result.source_id,
                schema_name=result.schema_name,
                row_count=result.row_count,
                column_count=result.column_count,
                check_count=len(result.checks),
                status=result.status,
                last_run_at=now,
                created_at=now,
            ).on_conflict_do_update(
                index_elements=["id"],
                set_={
                    "row_count": result.row_count,
                    "column_count": result.column_count,
                    "check_count": len(result.checks),
                    "status": result.status,
                    "last_run_at": now,
                },
            )
            await db.execute(stmt)

            for chk in result.checks:
                db.add(CheckRun(
                    dataset_id=result.table,
                    column_name=chk.column,
                    detector_slug="null_fraction",
                    score=chk.null_fraction,
                    verdict=chk.verdict,
                    plain_english=chk.message,
                    details={
                        "null_count": chk.null_count,
                        "total_count": chk.total,
                        "null_fraction": chk.null_fraction,
                    },
                    ran_at=now,
                ))
            await db.commit()

        await self._sync_incidents(result, now)

    async def _sync_incidents(self, result: TableCheckResult, now: datetime) -> None:
        if AsyncSessionLocal is None:
            return

        async with AsyncSessionLocal() as db:
            existing_q = await db.execute(
                select(Incident).where(
                    Incident.dataset_id == result.table,
                    Incident.status == "open",
                    Incident.detector_slug == "null_fraction",
                )
            )
            existing: list[Incident] = list(existing_q.scalars().all())
            existing_cols = {i.column_name for i in existing}

            failing_cols = {
                chk.column
                for chk in result.checks
                if chk.verdict in ("fail", "warn")
            }

            for chk in result.checks:
                if chk.verdict in ("fail", "warn") and chk.column not in existing_cols:
                    db.add(Incident(
                        dataset_id=result.table,
                        column_name=chk.column,
                        detector_slug="null_fraction",
                        severity=chk.verdict,
                        message=f"{result.table}.{chk.column}: {chk.message}",
                        status="open",
                        opened_at=now,
                    ))

            for inc in existing:
                if inc.column_name not in failing_cols:
                    inc.status = "resolved"
                    inc.resolved_at = now

            await db.commit()

    async def _persist_user_check_results(
        self, table: str, results: list[dict], now: datetime, row_count: int | None = None
    ) -> None:
        if not results or AsyncSessionLocal is None:
            return
        from sqlalchemy import func as _func
        async with AsyncSessionLocal() as db:
            for r in results:
                db.add(CheckRun(
                    dataset_id=table,
                    column_name=r["column"],
                    detector_slug=r["detector_slug"],
                    score=r["score"],
                    verdict=r["verdict"],
                    plain_english=r["plain_english"],
                    details=r["details"],
                    ran_at=now,
                ))
            # Keep Dataset metadata in sync
            count_q = await db.execute(
                select(_func.count(ColumnCheck.id)).where(
                    ColumnCheck.dataset_id == table,
                    ColumnCheck.enabled.is_(True),
                )
            )
            check_count = count_q.scalar() or len(results)
            update_vals: dict = {"last_run_at": now, "check_count": check_count}
            if row_count is not None:
                update_vals["row_count"] = row_count
            await db.execute(
                sa_update(Dataset).where(Dataset.id == table).values(**update_vals)
            )
            await db.commit()

    # ------------------------------------------------------------------
    # Column profile (distribution) -- for per-column detail page
    # ------------------------------------------------------------------

    def _profile_column_sync(
        self, adapter: Any, schema: str, table: str, column: str
    ) -> dict:
        """Return value-distribution profile for a single column."""
        try:
            type_result = adapter._client.query(
                f"SELECT type FROM system.columns "
                f"WHERE database = '{schema}' AND table = '{table}' AND name = '{column}' LIMIT 1"
            )
            if not type_result.result_rows:
                return {"kind": "unknown", "column": column}
            raw_type = type_result.result_rows[0][0]
            base_type = raw_type.replace("Nullable(", "").rstrip(")")
            is_numeric = any(t in base_type for t in ("Int", "Float", "Decimal", "UInt"))
            if is_numeric:
                return self._numeric_profile(adapter, schema, table, column, raw_type)
            return self._categorical_profile(adapter, schema, table, column, raw_type)
        except Exception as exc:
            log.error("column_profile_failed", table=table, column=column, error=str(exc))
            return {"kind": "error", "column": column, "error": str(exc)}

    def _numeric_profile(
        self, adapter: Any, schema: str, table: str, column: str, col_type: str
    ) -> dict:
        stats_sql = (
            f"SELECT count(*) AS n,"
            f" toFloat64(min(`{column}`)) AS mn,"
            f" toFloat64(max(`{column}`)) AS mx,"
            f" toFloat64(avg(`{column}`)) AS mean,"
            f" toFloat64(stddevSamp(`{column}`)) AS std,"
            f" toFloat64(quantileExact(0.02)(`{column}`)) AS p2,"
            f" toFloat64(quantileExact(0.25)(`{column}`)) AS p25,"
            f" toFloat64(quantileExact(0.50)(`{column}`)) AS p50,"
            f" toFloat64(quantileExact(0.75)(`{column}`)) AS p75,"
            f" toFloat64(quantileExact(0.98)(`{column}`)) AS p98"
            f" FROM `{schema}`.`{table}` WHERE isNotNull(`{column}`)"
        )
        result = adapter._client.query(stats_sql)
        if not result.result_rows or not result.result_rows[0][0]:
            return {
                "kind": "numeric", "column": column, "data_type": col_type,
                "buckets": [], "stats": {}, "total_count": 0,
            }

        row = result.result_rows[0]
        total = int(row[0])
        mn, mx, mean, std = float(row[1]), float(row[2]), float(row[3]), float(row[4])
        p2, p25, p50, p75, p98 = float(row[5]), float(row[6]), float(row[7]), float(row[8]), float(row[9])

        iqr = p75 - p25
        fence_lo = p25 - 1.5 * iqr
        fence_hi = p75 + 1.5 * iqr

        n_bins = 20
        lo, hi = p2, p98
        if hi <= lo:
            return {
                "kind": "numeric", "column": column, "data_type": col_type,
                "stats": {
                    "min": mn, "max": mx, "mean": mean, "stddev": std,
                    "p25": p25, "p50": p50, "p75": p75,
                    "outlier_lower": fence_lo, "outlier_upper": fence_hi,
                    "total_count": total, "outlier_low_count": 0, "outlier_high_count": 0,
                },
                "buckets": [{"lower": lo, "upper": lo, "count": total, "is_outlier": False}],
            }

        bucket_width = (hi - lo) / n_bins
        hist_sql = (
            f"SELECT multiIf(`{column}` < {lo}, -1,"
            f" `{column}` >= {hi}, {n_bins},"
            f" toInt32(floor((`{column}` - {lo}) / {bucket_width}))) AS bi,"
            f" count(*) AS freq"
            f" FROM `{schema}`.`{table}` WHERE isNotNull(`{column}`)"
            f" GROUP BY bi ORDER BY bi"
        )
        hist = adapter._client.query(hist_sql)
        counts: dict[int, int] = {int(r[0]): int(r[1]) for r in hist.result_rows}

        buckets = []
        for i in range(n_bins):
            lower = lo + i * bucket_width
            upper = lo + (i + 1) * bucket_width
            is_outlier = upper <= fence_lo or lower >= fence_hi
            buckets.append({
                "lower": round(lower, 6), "upper": round(upper, 6),
                "count": counts.get(i, 0), "is_outlier": is_outlier,
            })

        return {
            "kind": "numeric", "column": column, "data_type": col_type,
            "stats": {
                "min": round(mn, 6), "max": round(mx, 6),
                "mean": round(mean, 6), "stddev": round(std, 6),
                "p25": round(p25, 6), "p50": round(p50, 6), "p75": round(p75, 6),
                "outlier_lower": round(fence_lo, 6), "outlier_upper": round(fence_hi, 6),
                "total_count": total,
                "outlier_low_count": counts.get(-1, 0),
                "outlier_high_count": counts.get(n_bins, 0),
            },
            "buckets": buckets,
        }

    def _categorical_profile(
        self, adapter: Any, schema: str, table: str, column: str, col_type: str
    ) -> dict:
        total_result = adapter._client.query(
            f"SELECT count(*) FROM `{schema}`.`{table}` WHERE isNotNull(`{column}`)"
        )
        top_result = adapter._client.query(
            f"SELECT toString(`{column}`) AS v, count(*) AS freq"
            f" FROM `{schema}`.`{table}` WHERE isNotNull(`{column}`)"
            f" GROUP BY `{column}` ORDER BY freq DESC LIMIT 15"
        )
        total = int(total_result.result_rows[0][0]) if total_result.result_rows else 0
        top_values = [{"value": str(r[0]), "count": int(r[1])} for r in top_result.result_rows]
        shown = sum(v["count"] for v in top_values)
        return {
            "kind": "categorical", "column": column, "data_type": col_type,
            "total_count": total, "top_values": top_values, "other_count": total - shown,
        }


# Module-level singleton
check_runner = CheckRunner()
