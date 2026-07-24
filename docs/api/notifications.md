# Notifications

dqt ships a `SlackNotifier`, `EmailNotifier`, and a `suite_to_slack_blocks` formatter that converts a `SuiteResult` into a Slack Block Kit payload.

No bot token is required for Slack — Incoming Webhooks only.

---

## Quick start: suite report to Slack

Run a check suite and post the results to a Slack channel in three lines:

```python
from dqt import Runner, MemoryStore, Check
from dqt.adapters.local import LocalAdapter
from dqt.notifications import SlackNotifier
import pandas as pd

df = pd.read_csv("orders.csv")
adapter = LocalAdapter({"public.orders": df})

checks = [
    Check(schema_name="public", table_name="orders",
          column_name="amount", detector_slug="iqr_fence", params={"k": 3.0}),
    Check(schema_name="public", table_name="orders",
          column_name="customer_id", detector_slug="null_fraction"),
    Check(schema_name="public", table_name="orders",
          detector_slug="volume_change_ratio"),
]

suite = Runner(MemoryStore()).run_suite(checks, adapter)

SlackNotifier().send_suite_report(suite, title="orders nightly checks")
# SLACK_WEBHOOK_URL env var is read automatically.
# Or pass explicitly: SlackNotifier(webhook_url="https://hooks.slack.com/...")
```

The Slack message contains:
- Header with the suite title
- Summary line: `N passed · N warned · N failed · N skipped`
- One row per check at or above the configured `level` (fail-first, then warn)
- Footer with budget spent vs total

---

## `send_suite_report`

```python
SlackNotifier.send_suite_report(
    suite,
    *,
    title: str = "dqt check suite",
    level: str = "warn",          # "all" | "warn" | "fail"
) -> bool
```

| `level` | Rows shown in message |
|---------|----------------------|
| `"all"` | pass + warn + fail |
| `"warn"` | warn + fail (default) |
| `"fail"` | fail only |

The summary counts are always complete regardless of `level`. The footer shows `showing: <level>+` so readers know the list is filtered.

```python
# Only post failures (tight CI gate)
notifier.send_suite_report(suite, title="nightly orders", level="fail")

# Warnings and failures (default, good for scheduled jobs)
notifier.send_suite_report(suite, title="nightly orders", level="warn")

# Every check including passes (verbose audit trail)
notifier.send_suite_report(suite, title="nightly orders", level="all")
```

Returns `True` if the webhook responded 200, `False` on any error (network failure, bad webhook URL, missing env var).

---

## `suite_to_slack_blocks`

Build the Block Kit payload without sending it — useful for custom dispatch, logging, or testing:

```python
from dqt.notifications import suite_to_slack_blocks

blocks = suite_to_slack_blocks(suite, title="orders nightly checks", level="warn")

# inspect
import json
print(json.dumps(blocks, indent=2))

# send yourself
SlackNotifier(webhook_url=url).send_blocks(blocks, text="dqt alert: orders checks")
```

---

## `SlackNotifier` primitives

```python
from dqt.notifications import SlackNotifier

notifier = SlackNotifier()                                 # reads SLACK_WEBHOOK_URL
notifier = SlackNotifier(webhook_url="https://hooks.slack.com/services/...")

# Plain text
notifier.send_text("dqt: 2 checks failed on orders")

# Block Kit (full control)
notifier.send_blocks([
    {"type": "header", "text": {"type": "plain_text", "text": ":red_circle: dqt FAIL"}},
    {"type": "section", "text": {"type": "mrkdwn", "text": "orders.amount: IQR fence breached"}},
], text="dqt FAIL: orders checks")
```

---

## `EmailNotifier`

```python
from dqt.notifications import EmailNotifier

notifier = EmailNotifier(host="smtp.yourcompany.com", port=587)
notifier.send(
    to="data-team@yourcompany.com",
    subject="dqt FAIL: orders nightly checks",
    html="<p>2 checks failed. See dqt dashboard.</p>",
    plain="2 checks failed. See dqt dashboard.",
)
```

---

## Wiring into a scheduler

The simplest production pattern — run as a cron job or arq task:

```python
# scripts/nightly_checks.py
import os
from dqt import Runner, Check
from dqt.store.postgres import PostgresStore
from dqt.adapters.postgres import PostgresAdapter
from dqt.notifications import SlackNotifier

store = PostgresStore(os.environ["DATABASE_URL"])
adapter = PostgresAdapter(os.environ["WAREHOUSE_URL"])
checks = [...]  # load from YAML or DB

suite = Runner(store).run_suite(checks, adapter, cost_budget_usd=5.0)

SlackNotifier().send_suite_report(
    suite,
    title="nightly data quality checks",
    level="warn",   # only post when something is wrong
)
```

Run it:
```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/... python scripts/nightly_checks.py
```

Or as a GitHub Actions schedule:

```yaml
on:
  schedule:
    - cron: "0 6 * * *"   # 06:00 UTC daily
jobs:
  dqt:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install dqtlib[postgres]
      - run: python scripts/nightly_checks.py
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
          WAREHOUSE_URL: ${{ secrets.WAREHOUSE_URL }}
```
