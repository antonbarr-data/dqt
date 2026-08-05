"""dqt data quality CLI — argparse, zero new dependencies."""
from __future__ import annotations

import argparse
import sys


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _import_all_algorithm_modules() -> None:
    """Import every algorithm sub-package so detectors self-register via @registry.register."""
    import dqt.algorithms.basic  # noqa: F401
    import dqt.algorithms.distribution  # noqa: F401
    import dqt.algorithms.drift  # noqa: F401
    import dqt.algorithms.info  # noqa: F401
    import dqt.algorithms.outliers_multi  # noqa: F401
    import dqt.algorithms.outliers_uni  # noqa: F401
    import dqt.algorithms.pattern  # noqa: F401
    import dqt.algorithms.referential  # noqa: F401
    import dqt.algorithms.schema  # noqa: F401
    import dqt.algorithms.timeseries  # noqa: F401
    import dqt.algorithms.custom  # noqa: F401


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

def _cmd_list_detectors(_args: argparse.Namespace) -> None:
    """Print all registered detector slugs grouped by group name."""
    _import_all_algorithm_modules()
    from dqt.algorithms._registry import registry

    # Build group → [slug, ...] mapping
    groups: dict[str, list[str]] = {}
    for slug, cls in registry._map.items():
        g = getattr(cls, "group", "ungrouped")
        groups.setdefault(g, []).append(slug)

    for group_name in sorted(groups):
        print(f"\n[{group_name}]")
        for slug in sorted(groups[group_name]):
            print(f"  {slug}")


def _resolve_adapter(connection: str):
    """Instantiate the correct WarehouseAdapter from a connection string."""
    if connection.startswith("file://"):
        from dqt.adapters.local import LocalFileAdapter
        return LocalFileAdapter(connection[len("file://"):])
    if connection.startswith("postgresql://") or connection.startswith("postgres://"):
        from dqt.adapters.postgres.adapter import PostgresAdapter
        return PostgresAdapter(connection)
    raise ValueError(
        f"Unsupported connection scheme: '{connection}'. "
        "Supported: file://<path>, postgresql://<...>"
    )


def _results_to_json(results) -> str:
    import json
    return json.dumps({
        "results": [
            {
                "check_id": str(r.check_id),
                "detector_slug": r.detector_slug,
                "verdict": r.verdict.value,
                "score": r.score,
                "plain_english": r.plain_english,
            }
            for r in results
        ]
    }, indent=2)


def _results_to_junit(results) -> str:
    from xml.etree.ElementTree import Element, SubElement, tostring
    suites = Element("testsuites")
    suite = SubElement(suites, "testsuite", name="dqt", tests=str(len(results)))
    for r in results:
        tc = SubElement(suite, "testcase", name=r.detector_slug,
                        classname=str(r.check_id), time="0")
        if r.verdict.value == "fail":
            failure = SubElement(tc, "failure", message=r.plain_english)
            failure.text = r.plain_english
        elif r.verdict.value == "warn":
            SubElement(tc, "system-out").text = r.plain_english
    try:
        from xml.etree.ElementTree import indent as et_indent
        et_indent(suites)
    except (ImportError, TypeError):
        pass
    return '<?xml version="1.0"?>\n' + tostring(suites, encoding="unicode")


def _cmd_run(args: argparse.Namespace) -> None:
    """Load a YAML check file. With --connection, execute checks against the adapter."""
    from dqt.checks.loader import load_checks_file, CheckValidationError

    try:
        checks = load_checks_file(args.yaml_file)
    except FileNotFoundError:
        print(f"error: file not found: {args.yaml_file}", file=sys.stderr)
        sys.exit(1)
    except CheckValidationError as exc:
        print(f"error: invalid check YAML: {exc}", file=sys.stderr)
        sys.exit(1)

    if not checks:
        print("No checks defined in file.")
        return

    if not getattr(args, "connection", None):
        for check in checks:
            print(
                f"run: {check.detector_slug}  "
                f"[{check.schema_name}.{check.table_name}"
                + (f".{check.column_name}" if check.column_name else "")
                + "]"
            )
        print("\nNote: pass --connection <url> to execute checks.")
        return

    adapter = _resolve_adapter(args.connection)
    from dqt.store.memory import MemoryStore
    from dqt.runner.runner import Runner
    runner = Runner(MemoryStore())

    results = []
    any_fail = False
    for check in checks:
        try:
            result = runner.run(check, adapter)
            results.append(result)
            if result.verdict.value == "fail":
                any_fail = True
        except Exception as exc:
            print(f"error running {check.detector_slug}: {exc}", file=sys.stderr)
            any_fail = True

    output_fmt = getattr(args, "output", "text")
    if output_fmt == "json":
        print(_results_to_json(results))
    elif output_fmt == "junit":
        print(_results_to_junit(results))
    else:
        for r in results:
            print(f"[{r.verdict.value.upper():4s}] {r.detector_slug}: {r.plain_english}")

    sys.exit(1 if any_fail else 0)


def _cmd_fit(args: argparse.Namespace) -> None:
    """Load a YAML check file and print fit targets (adapter required to execute)."""
    from dqt.checks.loader import load_checks_file, CheckValidationError

    try:
        checks = load_checks_file(args.yaml_file)
    except FileNotFoundError:
        print(f"error: file not found: {args.yaml_file}", file=sys.stderr)
        sys.exit(1)
    except CheckValidationError as exc:
        print(f"error: invalid check YAML: {exc}", file=sys.stderr)
        sys.exit(1)

    if not checks:
        print("No checks defined in file.")
        return

    for check in checks:
        print(f"fit: {check.id}")

    print(
        "\nNote: adapter required to fit — use the Python API with a WarehouseAdapter."
    )


def _cmd_dashboard(args: argparse.Namespace) -> None:
    """Start the local dqt dashboard (requires dqtlib[dashboard])."""
    import os
    import secrets

    token = getattr(args, "token", None)
    generate_token = getattr(args, "generate_token", False)

    if token and generate_token:
        print("error: --token and --generate-token are mutually exclusive", file=sys.stderr)
        sys.exit(1)

    if generate_token:
        new_token = secrets.token_hex(32)
        print(new_token)
        os.environ["DQT_DASHBOARD_TOKEN"] = new_token
    elif token:
        os.environ["DQT_DASHBOARD_TOKEN"] = token

    try:
        import uvicorn
        from dqt.dashboard.app import build_app
    except ImportError:
        print("error: dqtlib[dashboard] is required. Run: pip install 'dqtlib[dashboard]'",
              file=sys.stderr)
        sys.exit(1)

    from dqt.store.memory import MemoryStore
    app = build_app(store=MemoryStore())
    if not generate_token and not token:
        print("warning: no token set -- dashboard is open to anyone on the network", file=sys.stderr)
    print(f"dqt dashboard -> http://{args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port)


def _cmd_wiki_sync(args: argparse.Namespace) -> None:
    """Synthesise wiki/ entries from raw/ documents using Anthropic Claude."""
    from pathlib import Path
    from dqt.wiki.loader import load_raw_documents
    from dqt.wiki.synthesizer import synthesize_entries
    from dqt.wiki.writer import load_manifest, write_wiki

    raw_path = Path(args.raw_dir)
    wiki_path = Path(args.wiki_dir)

    if not raw_path.exists():
        print(f"error: raw_dir not found: {args.raw_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"Loading documents from {args.raw_dir}")
    docs = load_raw_documents(raw_path)
    if not docs:
        print("No documents found -- nothing to sync.")
        return
    print(f"  {len(docs)} document(s) found")

    manifest = load_manifest(wiki_path, args.raw_dir, str(wiki_path))

    def _progress(msg: str) -> None:
        print(f"  > {msg}")

    try:
        entries = synthesize_entries(
            docs, manifest,
            model=args.model,
            force=args.force,
            progress=_progress,
        )
    except (ImportError, EnvironmentError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)

    if not entries:
        print("All entries up to date.")
        return

    write_wiki(entries, wiki_path, manifest)
    print(f"Wrote {len(entries)} wiki entry/entries to {args.wiki_dir}")


def _cmd_wiki_status(args: argparse.Namespace) -> None:
    """Show which raw documents are synced and which need re-synthesis."""
    from pathlib import Path
    from dqt.wiki.loader import load_raw_documents
    from dqt.wiki.writer import load_manifest
    from dqt.wiki.synthesizer import _content_hash, _entry_id

    raw_path = Path(args.raw_dir)
    wiki_path = Path(args.wiki_dir)

    docs = load_raw_documents(raw_path)
    manifest = load_manifest(wiki_path, args.raw_dir, str(wiki_path))

    groups: dict[str, list] = {}
    for doc in docs:
        parts = Path(doc.path).parts
        group_key = parts[0] if len(parts) > 1 else "__root__"
        groups.setdefault(group_key, []).append(doc)

    for group_key, group_docs in sorted(groups.items()):
        entry_id = _entry_id([d.path for d in group_docs])
        hash_val = _content_hash(group_docs)
        last_hash = manifest.entries.get(entry_id)
        if last_hash is None:
            status = "pending"
        elif last_hash == hash_val:
            status = "up to date"
        else:
            status = "changed"
        print(f"  {group_key:30s} {len(group_docs):3d} docs  {status}")

    if manifest.last_sync:
        print(f"\nLast full sync: {manifest.last_sync}")


def _cmd_demo(_args: argparse.Namespace) -> None:
    """Generate a synthetic demo: 30% level shift in 'revenue', run wasserstein_1, print result."""
    import numpy as np
    import pandas as pd

    from dqt.algorithms.drift.wasserstein import Wasserstein1Detector

    rng = np.random.default_rng(42)

    # 90 rows of stable reference data, then 30 rows with a 30% level shift
    base = rng.normal(loc=100.0, scale=10.0, size=90)
    shifted = rng.normal(loc=130.0, scale=10.0, size=30)  # +30% level shift

    reference = pd.DataFrame({"revenue": base})
    current = pd.DataFrame({"revenue": shifted})

    detector = Wasserstein1Detector()
    state = detector.fit(reference)
    result = detector.score(current, state)

    # Use sys.stdout.buffer for byte-safe output on Windows consoles
    def _print(s: str) -> None:
        sys.stdout.buffer.write((s + "\n").encode("utf-8", errors="replace"))
        sys.stdout.buffer.flush()

    _print("=== dqt demo: wasserstein_1 on synthetic 'revenue' column ===")
    _print(f"Reference rows : {len(reference)}")
    _print(f"Current rows   : {len(current)}  (30% level shift at row 90)")
    _print(f"Score          : {result.score:.4f}")
    _print(f"Verdict        : {result.verdict.value}")
    _print(f"Summary        : {result.plain_english}")
    _print(f"Details        : {result.details}")


def _cmd_compile(args: argparse.Namespace) -> None:
    """Compile a dqt YAML check file to the target format."""
    from dqt.checks.loader import load_checks_file, CheckValidationError

    try:
        checks = load_checks_file(args.yaml_file)
    except FileNotFoundError:
        print(f"error: file not found: {args.yaml_file}", file=sys.stderr)
        sys.exit(1)
    except CheckValidationError as exc:
        print(f"error: invalid check YAML: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.to == "dbt":
        from dqt.compat.dbt_tests import checks_to_dbt_yaml
        print(checks_to_dbt_yaml(checks))
    else:
        print(f"error: unknown target '{args.to}'", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

_FORMAT_LABEL = {"okf": "Google OKF", "ossie": "Apache Ossie"}


def _repo_poll(httpx, base: str, proposal_id: str) -> dict:
    import time
    for _ in range(80):
        r = httpx.get(f"{base}/api/v1/proposals/{proposal_id}", timeout=30)
        r.raise_for_status()
        data = r.json()
        if data["status"] in ("ready", "failed"):
            return data
        time.sleep(1.5)
    raise SystemExit("Timed out waiting for extraction.")


def _repo_print(payload: dict) -> None:
    print(f"\nExtracted from {len(payload.get('sources_seen', []))} file(s):")
    for d in payload.get("datasets", []):
        badge = "in source" if d.get("available") else "NOT IN SOURCE"
        fmt = _FORMAT_LABEL.get((d.get("provenance") or [{}])[0].get("format", ""), "")
        print(f"  dataset {d['id']}  [{fmt}] [{badge}]")
        for c in d.get("columns", []):
            flags = " ".join(f for f, on in (("pk", c["primary_key"]), ("time", c["is_time"]), ("metric", c["is_metric"])) if on)
            avail = "" if c.get("available") else "  (not in source)"
            print(f"      col {c['name']}: {c.get('live_data_type') or c.get('data_type') or ''} {flags}{avail}")
        for m in d.get("metrics", []):
            print(f"      metric {m['name']} ({m['kind']}) {m.get('expression') or ''}")
    print(f"  checks (disabled): {len(payload.get('checks', []))}")
    kn = payload.get("knowledge", [])
    if kn:
        print(f"  knowledge: {', '.join(k['title'] for k in kn)}")
    if payload.get("conflicts"):
        print(f"  conflicts: {len(payload['conflicts'])}")


def _repo_apply_all(httpx, base: str, proposal_id: str, payload: dict) -> None:
    datasets = [d for d in payload.get("datasets", []) if d.get("available")]
    ids = {d["id"] for d in datasets}
    body = {
        "dataset_ids": list(ids),
        "metric_ids": [m["id"] for d in datasets for m in d.get("metrics", [])],
        "check_ids": [c["id"] for c in payload.get("checks", []) if c["dataset"] in ids],
        "knowledge_ids": [k["id"] for k in payload.get("knowledge", [])],
    }
    r = httpx.post(f"{base}/api/v1/proposals/{proposal_id}/apply", json=body, timeout=60)
    r.raise_for_status()
    c = r.json().get("created", {})
    print(f"\nImported: {c.get('datasets',0)} dataset(s), {c.get('metrics',0)} metric(s), "
          f"{c.get('checks',0)} check(s), {c.get('knowledge',0)} note(s).")


def _cmd_repo(args: argparse.Namespace) -> None:
    """Connect Google OKF / Apache Ossie repos to a Source and import from them."""
    import httpx
    base = args.server.rstrip("/")
    if args.repo_command == "list":
        r = httpx.get(f"{base}/api/v1/sources/{args.source}/repos", timeout=30)
        r.raise_for_status()
        repos = r.json()
        if not repos:
            print("No repos connected.")
            return
        for repo in repos:
            print(f"{repo['id']}  {repo['status']:<10}  {repo['git_url']}  (commit {repo.get('last_commit') or '-'})")
        return

    if args.repo_command == "add":
        r = httpx.post(f"{base}/api/v1/sources/{args.source}/repos",
                       json={"git_url": args.git_url, "branch": args.branch, "subpath": args.subpath}, timeout=60)
    else:  # sync
        r = httpx.post(f"{base}/api/v1/repos/{args.repo_id}/sync", timeout=60)
    if r.status_code >= 400:
        raise SystemExit(f"ERROR: {r.status_code} {r.text}")
    proposal_id = r.json()["proposal_id"]
    print(f"Extracting (proposal {proposal_id})...")
    data = _repo_poll(httpx, base, proposal_id)
    if data["status"] == "failed":
        raise SystemExit(f"Extraction failed: {data.get('error')}")
    _repo_print(data["payload"])
    if getattr(args, "all", False):
        _repo_apply_all(httpx, base, proposal_id, data["payload"])
    else:
        print("\nRe-run with --all to import, or use the web UI to select a subset.")


def main() -> None:
    parser = argparse.ArgumentParser(prog="dqt", description="dqt data quality CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    # list-detectors
    sub.add_parser("list-detectors", help="List all registered detector slugs by group")

    # run <yaml_file>
    p_run = sub.add_parser("run", help="Run checks; pass --connection to execute against an adapter")
    p_run.add_argument("yaml_file", help="Path to the YAML check file")
    p_run.add_argument("--connection", default=None,
                       help="Connection string, e.g. file:///path/to/data.csv or postgresql://...")
    p_run.add_argument("--output", choices=["text", "json", "junit"], default="text",
                       help="Output format (default: text)")

    # fit <yaml_file>
    p_fit = sub.add_parser("fit", help="Validate a check YAML file and print fit targets")
    p_fit.add_argument("yaml_file", help="Path to the YAML check file")

    # compile <yaml_file> --to dbt
    p_compile = sub.add_parser("compile", help="Compile checks to another format (e.g. dbt)")
    p_compile.add_argument("yaml_file", help="Path to the YAML check file")
    p_compile.add_argument("--to", required=True, choices=["dbt"],
                           help="Target format")

    # demo
    sub.add_parser("demo", help="Run a synthetic in-memory demo with wasserstein_1")

    # dashboard
    p_dashboard = sub.add_parser("dashboard", help="Start the local dqt dashboard (requires dqtlib[dashboard])")
    p_dashboard.add_argument("--port", "-p", type=int, default=8080, help="Port to listen on (default: 8080)")
    p_dashboard.add_argument("--host", default="127.0.0.1", help="Host to bind (default: 127.0.0.1)")
    p_dashboard.add_argument("--token", default=None,
                             help="Bearer token to protect the dashboard")
    p_dashboard.add_argument("--generate-token", action="store_true",
                             help="Generate a random token, print it, and set it")

    # wiki
    wiki_parser = sub.add_parser("wiki", help="LLM wiki synthesis from raw documents")
    wiki_sub = wiki_parser.add_subparsers(dest="wiki_command", required=True)

    p_wiki_sync = wiki_sub.add_parser("sync", help="Synthesise wiki entries from raw documents")
    p_wiki_sync.add_argument("raw_dir", help="Path to raw/ source documents folder")
    p_wiki_sync.add_argument("wiki_dir", help="Path to wiki/ output folder")
    p_wiki_sync.add_argument("--model", default=None,
                             help="Override the model (default: the configured LLM's model)")
    p_wiki_sync.add_argument("--force", action="store_true",
                             help="Re-synthesise all entries even if unchanged")

    p_wiki_status = wiki_sub.add_parser("status", help="Show sync status for all raw documents")
    p_wiki_status.add_argument("raw_dir", help="Path to raw/ source documents folder")
    p_wiki_status.add_argument("wiki_dir", help="Path to wiki/ output folder")

    # repo (Google OKF / Apache Ossie ingest)
    repo_parser = sub.add_parser("repo", help="Connect Google OKF / Apache Ossie repos to a Source")
    repo_sub = repo_parser.add_subparsers(dest="repo_command", required=True)

    p_repo_add = repo_sub.add_parser("add", help="Register a repo against a Source and extract a proposal")
    p_repo_add.add_argument("git_url", help="Git URL (or local path) of a Google OKF / Apache Ossie repo")
    p_repo_add.add_argument("--source", required=True, help="Existing Source id to bind and import into")
    p_repo_add.add_argument("--branch", default=None, help="Git branch")
    p_repo_add.add_argument("--subpath", default=None, help="Subdirectory within the repo")
    p_repo_add.add_argument("--server", "-s", default="http://localhost:8000", help="dqt server URL")
    p_repo_add.add_argument("--all", action="store_true", help="Import all source-present items (default: print only)")

    p_repo_sync = repo_sub.add_parser("sync", help="Re-pull a repo and re-extract a proposal")
    p_repo_sync.add_argument("repo_id", help="Knowledge repo id")
    p_repo_sync.add_argument("--server", "-s", default="http://localhost:8000", help="dqt server URL")
    p_repo_sync.add_argument("--all", action="store_true", help="Import all source-present items after re-extraction")

    p_repo_list = repo_sub.add_parser("list", help="List repos connected to a Source")
    p_repo_list.add_argument("--source", required=True, help="Source id")
    p_repo_list.add_argument("--server", "-s", default="http://localhost:8000", help="dqt server URL")

    args = parser.parse_args()

    if args.command == "repo":
        _cmd_repo(args)
        return

    if args.command == "wiki":
        if args.wiki_command == "sync":
            _cmd_wiki_sync(args)
        elif args.wiki_command == "status":
            _cmd_wiki_status(args)
        return

    dispatch = {
        "list-detectors": _cmd_list_detectors,
        "run": _cmd_run,
        "fit": _cmd_fit,
        "compile": _cmd_compile,
        "demo": _cmd_demo,
        "dashboard": _cmd_dashboard,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
