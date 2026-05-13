# Recipe 18: End-to-end - raw docs to wiki using dqt wiki sync

## Problem

Data teams accumulate knowledge in Google Docs, Notion pages, Confluence, and README
files. When a metric incident fires, the on-call engineer has no reliable way to
find what the metric means, who owns it, or what broke it last time. dqt's wiki sync
ingests these raw docs, embeds them, and surfaces them in the incident detail panel
and Cmd-K search.

## dqt check

There is no statistical check for this recipe. The workflow uses `dqt wiki sync`
to ingest documentation and `dqt wiki link` to associate docs with datasets/metrics.

```bash
# Sync a directory of Markdown docs into the dqt catalog
dqt wiki sync ./docs/metrics/ \
  --format markdown \
  --namespace metrics \
  --embed

# Sync a Notion workspace (requires NOTION_TOKEN in .env)
dqt wiki sync notion://my-workspace/data-docs \
  --namespace data-catalog \
  --embed

# Link a specific doc to a metric
dqt wiki link \
  --doc "metrics/order_revenue.md" \
  --metric order_revenue_7d_rolling

# Link a doc to a dataset
dqt wiki link \
  --doc "data-catalog/fct_orders.md" \
  --dataset dw.fct_orders
```

Governance YAML to require documentation coverage:

```yaml
# governance/policies/documentation_coverage.yaml
policy_id: require_metric_docs
description: All metrics in domain=finance must have linked wiki pages
rules:
  - target: metrics
    filter: "domain = 'finance'"
    require:
      - wiki_pages_count >= 1
      - wiki_last_updated_days <= 90
severity: warn
```

## Expected output

```
Syncing ./docs/metrics/ (14 files)...
  embedded:  14
  linked:     9  (5 unlinked - run: dqt wiki link --suggest)

Wiki coverage: 9/14 metrics documented
Governance check: documentation_coverage  WARN  5 finance metrics unlinked
```

After running the link suggestions:

```
Suggested links (confidence >= 0.85):
  metrics/gross_margin.md  -> metric:gross_margin_pct  [0.94]
  metrics/arr.md           -> metric:annual_recurring_revenue  [0.91]
Accept all? [y/N]
```

On an incident, the detail panel shows the linked wiki page inline with the
statistical evidence, plus a "similar incidents" panel powered by the embeddings.

## Why this approach

Embedding docs into pgvector at ingest time means incident search is semantic, not
keyword-based. "What caused revenue to drop last quarter?" returns the incident
where the discount_amount backfill fired, not just incidents with "revenue" in the
title. The governance policy enforces documentation coverage passively - teams see
WARN badges on undocumented metrics in the catalog without a separate compliance
process.
