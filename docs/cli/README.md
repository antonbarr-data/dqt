# dqt CLI reference

## Installation

```bash
pip install dqt-cli
```

The CLI requires `dqt` as a dependency and installs it automatically.

## Commands

| Command | Description |
|---|---|
| `dqt run <manifest>` | Run all checks in a manifest YAML file |
| `dqt version` | Print library version |
| `dqt demo seed` | Seed demo data into the local database |
| `dqt demo reset` | Reset demo data |

---

## `dqt run`

```
dqt run [OPTIONS] MANIFEST_PATH
```

Loads a manifest YAML, connects to the specified source, fits baselines, scores all checks, and prints results.

### Options

| Option | Default | Description |
|---|---|---|
| `--fit / --no-fit` | `--fit` | Fit baselines before scoring. Pass `--no-fit` to score against a previously persisted state. |
| `--output`, `-o` | `table` | Output format: `table` (Rich terminal table) or `json` (newline-free JSON array). |

### Exit codes

| Code | Meaning |
|---|---|
| `0` | All checks passed (or only warnings) |
| `1` | Manifest file not found, or checks failed to parse |
| `2` | One or more checks returned `fail` verdict |

### JSON output

With `--output json`, each item in the array has the shape:

```json
{
  "check": "null_fraction",
  "table": "main.orders",
  "column": "customer_id",
  "verdict": "pass",
  "score": 0.0023,
  "plain_english": "23/10000 rows are NULL (0.2%)"
}
```

On error, the item has `{"check": "...", "error": "..."}`.

---

## Manifest YAML format

A manifest file has four top-level keys: `version`, `source`, `semantic`, and `checks`.

```yaml
version: "1"

source:
  type: duckdb                 # duckdb | csv | parquet
  database: warehouse.duckdb  # path to the DuckDB file; ":memory:" for in-memory

semantic:
  tables:
    - schema: main
      name: orders
      description: "One row per customer order."
      columns:
        - name: order_id
          description: "Surrogate key."
          classification: internal
          pii: false
        - name: email
          description: "Customer email."
          classification: confidential
          pii: true
        - name: amount
          description: "Order total in USD cents."
          unit: "USD cents"

checks:
  - schema_name: main
    table_name: orders
    column_name: customer_id
    detector_slug: null_fraction

  - schema_name: main
    table_name: orders
    detector_slug: volume

  - schema_name: main
    table_name: orders
    column_name: amount
    detector_slug: mad_outlier_fraction
    params:
      threshold: 3.5

  - schema_name: main
    table_name: orders
    column_name: amount
    detector_slug: ks_pvalue
    baseline:
      window_days: 14
      min_rows: 1000
    sample_n: 50000
```

### Source types

#### DuckDB file

```yaml
source:
  type: duckdb
  id: warehouse          # optional label
  database: data/warehouse.duckdb
```

#### CSV

The CSV is loaded into an in-memory DuckDB table. `table_name` sets the table name used in checks.

```yaml
source:
  type: csv
  path: data/orders.csv
  table_name: orders
```

#### Parquet

```yaml
source:
  type: parquet
  path: data/orders.parquet
  table_name: orders
```

#### PostgreSQL

PostgreSQL sources are not supported by the CLI adapter. Use the dqt server (`apps/server`) with a full `WarehouseAdapter` for Postgres, BigQuery, Snowflake, and other engines.

---

## Semantic layer definition

The `semantic` block annotates tables and columns with descriptions, classification, and PII flags. This metadata is not required for checks to run — it enriches the catalog and governs PII handling in the server.

```yaml
semantic:
  tables:
    - schema: analytics
      name: fct_orders
      description: "Fact table for completed orders."
      columns:
        - name: order_id
          description: "Surrogate order key."
          classification: internal   # public | internal | confidential | restricted
          pii: false
          unit: ""

        - name: customer_email
          description: "Customer billing email."
          classification: confidential
          pii: true

        - name: revenue_usd
          description: "Gross revenue in USD."
          classification: internal
          unit: "USD"
```

---

## Full annotated example

```yaml
version: "1"

# -------------------------------------------------------------------
# Source: a DuckDB file containing the warehouse export
# -------------------------------------------------------------------
source:
  type: duckdb
  id: local_warehouse
  database: ./data/warehouse.duckdb

# -------------------------------------------------------------------
# Semantic layer: descriptions, ownership, PII classification
# -------------------------------------------------------------------
semantic:
  tables:
    - schema: main
      name: fct_orders
      description: "One row per completed order."
      columns:
        - name: order_id
          classification: internal
          pii: false
        - name: customer_id
          classification: internal
          pii: false
        - name: email
          classification: confidential
          pii: true
        - name: amount_usd
          unit: "USD"
          classification: internal
          pii: false
        - name: created_at
          classification: internal
          pii: false
        - name: status
          classification: internal
          pii: false

# -------------------------------------------------------------------
# Checks
# -------------------------------------------------------------------
checks:

  # 1. Null fraction on a NOT NULL column
  - schema_name: main
    table_name: fct_orders
    column_name: order_id
    detector_slug: null_fraction

  # 2. Completeness — warn < 95 %, fail < 90 %
  - schema_name: main
    table_name: fct_orders
    column_name: customer_id
    detector_slug: completeness

  # 3. Row-count anomaly (table-level)
  - schema_name: main
    table_name: fct_orders
    detector_slug: volume

  # 4. Distribution drift via 2-sample KS test
  - schema_name: main
    table_name: fct_orders
    column_name: amount_usd
    detector_slug: ks_pvalue
    baseline:
      window_days: 14
      min_rows: 1000
    sample_n: 100000

  # 5. Robust outlier detection (MAD) — good for skewed revenue data
  - schema_name: main
    table_name: fct_orders
    column_name: amount_usd
    detector_slug: mad_outlier_fraction
    params:
      threshold: 3.5

  # 6. Double-MAD for asymmetric tails
  - schema_name: main
    table_name: fct_orders
    column_name: amount_usd
    detector_slug: double_mad_outlier_fraction
    params:
      threshold: 3.5

  # 7. Freshness check — warn after 1h, fail after 24h
  - schema_name: main
    table_name: fct_orders
    column_name: created_at
    detector_slug: freshness_seconds_behind
    params:
      col: created_at
      warn_seconds: 3600
      fail_seconds: 86400

  # 8. Set membership — status must be one of these values
  - schema_name: main
    table_name: fct_orders
    column_name: status
    detector_slug: set_membership
    params:
      allowed_values: [pending, processing, shipped, delivered, cancelled]

  # 9. Incremental scope — only rows since midnight UTC
  - schema_name: main
    table_name: fct_orders
    column_name: amount_usd
    detector_slug: null_fraction
    scope:
      mode: incremental
      key_col: created_at
      since: "2024-06-01T00:00:00"

  # 10. Filter — check only EU region
  - schema_name: main
    table_name: fct_orders
    column_name: amount_usd
    detector_slug: completeness
    filters:
      - col: region
        values: [EU]

  # 11. Sample 5 % instead of a fixed row count
  - schema_name: main
    table_name: fct_orders
    column_name: amount_usd
    detector_slug: ks_pvalue
    sampling_pct: 5.0
```

### Running this manifest

```bash
dqt run manifest.yaml
dqt run manifest.yaml --output json | jq '.[] | select(.verdict == "fail")'
dqt run manifest.yaml --no-fit   # skip re-fitting baselines
```
