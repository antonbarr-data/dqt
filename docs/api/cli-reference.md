# CLI Reference

Install the CLI:

```bash
pip install dqtlib
```

The `dqt` command is available after installation.

---

## `dqt version`

Print the installed library version.

```bash
$ dqt version
dqtlib 0.1.3
```

---

## `dqt run <manifest>`

Run all checks defined in a YAML manifest file.

```bash
dqt run checks/gigler.yaml
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--fit` / `--no-fit` | `--fit` | Fit baselines before scoring |
| `--output`, `-o` | `table` | Output format: `table` or `json` |

### Table output (default)

```bash
$ dqt run examples/gigler/checks.yaml

✓  public.gigler_transactions  null_fraction           amount_usd       0.00%  — within threshold
✓  public.gigler_transactions  uniqueness              transaction_id   100.0% — all values distinct
✓  public.gigler_transactions  set_membership          status           0.00%  — all values in set
⚠  public.gigler_transactions  mad_outlier_fraction    amount_usd       1.24%  — above 1% warn threshold
✗  public.gigler_transactions  ks_pvalue               amount_usd       0.992  — distribution shift detected (p < 0.01)
✓  public.gigler_transactions  volume                  —                2.1%   — within threshold
```

### JSON output

```bash
$ dqt run examples/gigler/checks.yaml --output json
[
  {
    "check_id": "...",
    "detector_slug": "null_fraction",
    "schema_name": "public",
    "table_name": "gigler_transactions",
    "column_name": "amount_usd",
    "verdict": "pass",
    "score": 0.0,
    "plain_english": "0.00% of values are null — within the 1% warn threshold"
  },
  ...
]
```

### Skip baseline fitting

If you've already fitted baselines in a previous run and want fast scoring only:

```bash
dqt run checks/gigler.yaml --no-fit
```

---

## YAML manifest for the CLI

The CLI reads the same YAML format as the Python API. See [YAML Reference](yaml-reference.md) for the complete field reference.

Minimal working example:

```yaml
version: "1"

source:
  type: csv
  id: gigler
  path: examples/gigler/data/gigler_transactions_2024_q2.csv
  table_name: gigler_transactions

checks:
  - schema_name: public
    table_name: gigler_transactions
    column_name: amount_usd
    detector_slug: null_fraction

  - schema_name: public
    table_name: gigler_transactions
    column_name: status
    detector_slug: set_membership
    params:
      allowed_values: [completed, cancelled, pending, refunded]

  - schema_name: public
    table_name: gigler_transactions
    column_name: amount_usd
    detector_slug: mad_outlier_fraction
    params:
      threshold: 3.5
```

Run it:

```bash
dqt run checks.yaml
```

---

## `dqt dashboard`

Start the local browser dashboard. Requires `pip install 'dqtlib[dashboard]'`.

```bash
dqt dashboard
dqt dashboard --port 9000
dqt dashboard --host 0.0.0.0 --port 8080
```

| Flag | Default | Description |
|------|---------|-------------|
| `--port`, `-p` | `8080` | Port to listen on |
| `--host` | `127.0.0.1` | Host to bind |

The CLI starts the dashboard with an empty in-memory store. To see real results, use `create_app(store=store)` from Python and pass the same store your `Runner` writes to. See [Local Dashboard guide](../dashboard.md) for the full workflow.

---

## Using in CI (GitHub Actions example)

```yaml
# .github/workflows/dq.yml
name: Data Quality

on:
  schedule:
    - cron: "0 6 * * *"   # daily at 06:00 UTC
  push:
    paths:
      - "checks/**"

jobs:
  dq:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install dqtlib
      - run: dqt run checks/gigler.yaml --output json > dq_results.json
      - uses: actions/upload-artifact@v4
        with:
          name: dq-results
          path: dq_results.json
```

Exit code is `0` if all checks pass, `1` if any check returns `fail`.
