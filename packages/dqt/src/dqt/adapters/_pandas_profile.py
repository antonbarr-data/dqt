"""Shared pandas-based profile_column implementation for adapters that sample into DataFrames."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pandas as pd

if TYPE_CHECKING:
    from dqt.adapters._protocol import ColumnProfileResult, WarehouseAdapter


def pandas_profile_column(
    adapter: "WarehouseAdapter",
    schema: str,
    table: str,
    column: str,
    log: Any,
) -> "ColumnProfileResult":
    from dqt.adapters._protocol import ColumnProfileResult
    try:
        cols_meta = adapter.describe_columns(schema, table)
        meta = next((c for c in cols_meta if c.name == column), None)
        if meta is None:
            raise ValueError(f"Column '{column}' not found in {schema}.{table}")

        data_type = meta.data_type
        numeric_hints = ("int", "float", "numeric", "decimal", "double", "real",
                         "bigint", "smallint", "money", "serial", "number", "integer",
                         "int64", "float64", "int32", "float32")
        is_numeric = any(t in data_type.lower() for t in numeric_hints)

        df = adapter.sample(schema, table, n=200_000)
        if column not in df.columns:
            return ColumnProfileResult(column=column)

        col_series = df[column]
        n_total = len(col_series)
        n_null = int(col_series.isna().sum())
        non_null_series = col_series.dropna()
        n_distinct = int(non_null_series.nunique())

        if is_numeric:
            numeric_col = pd.to_numeric(non_null_series, errors="coerce").dropna().astype(float)
            n_zero = int((numeric_col == 0).sum())
            if len(numeric_col) == 0:
                return ColumnProfileResult(
                    column=column, kind="numeric", data_type=data_type,
                    nullable=meta.nullable, position=meta.position,
                    total_count=n_total, null_count=n_null,
                    zero_count=0, empty_count=0, distinct_count=n_distinct,
                )
            p_min = float(numeric_col.min())
            p_max = float(numeric_col.max())
            p_mean = float(numeric_col.mean())
            p_stddev = float(numeric_col.std()) if len(numeric_col) > 1 else 0.0
            qs = numeric_col.quantile([0.02, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.98, 0.99])
            p2 = float(qs[0.02]); p5 = float(qs[0.05]); p10 = float(qs[0.10])
            p25 = float(qs[0.25]); p50 = float(qs[0.50]); p75 = float(qs[0.75])
            p90 = float(qs[0.90]); p95 = float(qs[0.95]); p98 = float(qs[0.98]); p99 = float(qs[0.99])

            buckets: list[dict] = []
            if p98 > p2:
                iqr = p75 - p25
                fence_lo = p25 - 1.5 * iqr
                fence_hi = p75 + 1.5 * iqr
                n_bins, bw = 20, (p98 - p2) / 20
                clipped = numeric_col.clip(p2, p98 - 1e-9)
                bin_idx = ((clipped - p2) / bw).astype(int).clip(0, n_bins - 1)
                counts = bin_idx.value_counts().to_dict()
                for i in range(n_bins):
                    lower = p2 + i * bw
                    upper = p2 + (i + 1) * bw
                    buckets.append({
                        "lower": round(lower, 6), "upper": round(upper, 6),
                        "count": int(counts.get(i, 0)),
                        "is_outlier": upper <= fence_lo or lower >= fence_hi,
                    })

            n_nn = len(non_null_series)
            top_q = non_null_series.value_counts().head(15)
            top_values = [
                {"value": str(v), "count": int(c),
                 "pct": round(int(c) / n_nn, 4) if n_nn > 0 else 0}
                for v, c in top_q.items()
            ]
            return ColumnProfileResult(
                column=column, kind="numeric", data_type=data_type,
                nullable=meta.nullable, position=meta.position,
                total_count=n_total, null_count=n_null,
                zero_count=n_zero, empty_count=0, distinct_count=n_distinct,
                p_min=p_min, p_max=p_max, p_mean=p_mean, p_stddev=p_stddev,
                p2=p2, p5=p5, p10=p10, p25=p25, p50=p50,
                p75=p75, p90=p90, p95=p95, p98=p98, p99=p99,
                histogram=buckets, top_values=top_values,
            )
        else:
            str_col = non_null_series.astype(str)
            n_empty = int((str_col.str.strip() == "").sum())
            n_nn = len(non_null_series)
            top_q = str_col.value_counts().head(20)
            top_values = [
                {"value": str(v), "count": int(c),
                 "pct": round(int(c) / n_nn, 4) if n_nn > 0 else 0}
                for v, c in top_q.items()
            ]
            return ColumnProfileResult(
                column=column, kind="categorical", data_type=data_type,
                nullable=meta.nullable, position=meta.position,
                total_count=n_total, null_count=n_null,
                zero_count=0, empty_count=n_empty, distinct_count=n_distinct,
                top_values=top_values,
            )
    except Exception as exc:
        log.error("profile_column failed", column=column, error=str(exc))
        raise
