# Local Dashboard

The local dashboard is a single-process web UI that shows your check results in a browser. It is designed for **notebook and laptop use** — run checks in Python, then open the dashboard to explore what happened. It requires no database, no server setup, and no auth.

Install the extras first:

```bash
pip install 'dqtlib[dashboard]'
```

---

## How it works

The dashboard reads from a **results store** — the same `MemoryStore` (or `PostgresStore`) that your `Runner` writes to. You populate the store by running checks, then point the dashboard at that same store. Both steps happen in the same Python process.

```
Runner.run(check, adapter)  →  store  ←  create_app(store=store)
                                               ↓
                                       http://localhost:8080
```

---

## Quickstart

```python
import pandas as pd
import uvicorn
from dqt import Runner, MemoryStore
from dqt.checks.models import Check, CheckScope
from dqt.dashboard import create_app

# 1. Shared store
store = MemoryStore()
runner = Runner(store)

# 2. Define and run a check
check = Check(
    detector_slug="wasserstein_1",
    scope=CheckScope(schema_name="default", table_name="revenue"),
)
reference = pd.DataFrame({"v": [100, 102, 98, 101, 99]})
current   = pd.DataFrame({"v": [130, 128, 135, 129, 132]})  # +30% shift

runner.run_in_memory(check, reference=reference, current=current)

# 3. Start the dashboard
app = create_app(store=store)
uvicorn.run(app, host="127.0.0.1", port=8080)
```

Open `http://127.0.0.1:8080` in your browser.

---

## What you see

**Index page (`/`)** — one row per check, showing the latest run:

| Check | Score | Verdict | Last run | Summary |
|---|---|---|---|---|
| `3fa85f64-...` | 0.4231 | warn | 2026-05-12 11:03 | Wasserstein distance 0.42 — above the 0.20 warn threshold |

Click any check ID to drill in.

**Detail page (`/checks/<id>`)** — KPI band at the top (score, verdict, timestamp), plain-English summary, and the full run history below.

**Health endpoint (`/health`)** — returns `{"status": "ok"}`. Useful for scripted checks that the server is up.

---

## CLI shortcut

If you just want to see the UI without writing Python:

```bash
dqt dashboard
```

Or on a different port:

```bash
dqt dashboard --port 9000
```

Or accessible from another machine on the network:

```bash
dqt dashboard --host 0.0.0.0 --port 8080
```

The CLI starts the dashboard with an **empty** in-memory store. The index page will say *"No check runs yet"* until you populate the store from a Python script and restart, or wire up a persistent store.

---

## Running checks then opening the dashboard (notebook pattern)

In a Jupyter notebook, run checks in one cell and start the dashboard in the next. Use `threading` so the server doesn't block the notebook kernel:

```python
# Cell 1 — run checks
import pandas as pd
from dqt import Runner, MemoryStore
from dqt.checks.models import Check, CheckScope

store = MemoryStore()
runner = Runner(store)

checks_and_data = [
    (Check(detector_slug="wasserstein_1",
           scope=CheckScope(schema_name="default", table_name="revenue")),
     pd.DataFrame({"v": [100]*90}),
     pd.DataFrame({"v": [130]*30})),

    (Check(detector_slug="mad_outlier_fraction",
           scope=CheckScope(schema_name="default", table_name="orders",
                            column_name="amount")),
     pd.DataFrame({"amount": [50, 51, 49, 52, 50]*20}),
     pd.DataFrame({"amount": [50, 51, 49, 52, 50]*19 + [9999, 0]})),
]

for check, ref, curr in checks_and_data:
    runner.run_in_memory(check, reference=ref, current=curr)

print(f"Ran {len(checks_and_data)} checks")
```

```python
# Cell 2 — start dashboard in background thread
import threading
import uvicorn
from dqt.dashboard import create_app

app = create_app(store=store)

thread = threading.Thread(
    target=uvicorn.run,
    kwargs={"app": app, "host": "127.0.0.1", "port": 8080},
    daemon=True,
)
thread.start()
print("Dashboard running at http://127.0.0.1:8080")
```

The `daemon=True` means the server stops when the notebook kernel stops — no cleanup needed.

---

## Python API

If you want to embed the dashboard in your own script or service:

```python
from dqt.dashboard import create_app
from dqt.store.memory import MemoryStore

store = MemoryStore()
app = create_app(store=store)
# app is a standard FastAPI application — pass it to uvicorn, gunicorn, or any ASGI server
```

`create_app` raises `ImportError` with a clear message if fastapi/uvicorn/jinja2 are not installed:

```
ImportError: dqt dashboard requires fastapi, uvicorn, and jinja2.
Install with: pip install 'dqtlib[dashboard]'
```

---

## When to use what

| Setup | When |
|---|---|
| Python script or notebook (above) | Best for ad-hoc investigation; single-file, no config |
| `dqt dashboard` CLI | Quick smoke test of the UI; useful if you run checks externally and share a persistent store |
| `apps/server` + `apps/web` | Production use; adds auth, multi-tenancy, scheduling, the full Next.js UI |

The local dashboard is intentionally minimal. It has no auth, no multi-tenancy, and no persistent storage beyond what your `store` object holds. For shared team use, the full server stack is the right choice.

---

## Limitations

- **In-memory store only, by default.** Results are lost when the Python process exits. Wire in `PostgresStore` if you need persistence across restarts.
- **`dqt dashboard` CLI starts with an empty store.** If you want the CLI to show real results, run your checks first and pass the same store to `create_app()` programmatically.
- **No auth.** Do not expose the dashboard port publicly.
- **Single-process.** The dashboard serves one request at a time; it is not designed for concurrent use.
