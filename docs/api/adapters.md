# Adapters

Adapters connect dqt to a data source. All adapters implement the `WarehouseAdapter` protocol.

## LocalAdapter

Wraps one or more in-memory DataFrames. No database required. Ideal for notebooks, CI, and unit tests.

```python
import pandas as pd
from dqt.adapters.local import LocalAdapter

df = pd.read_csv("examples/gigler/data/gigler_transactions_2024_q1.csv")

adapter = LocalAdapter({
    "public.gigler_transactions": df,
})
```

Pass multiple tables:

```python
adapter = LocalAdapter({
    "public.gigler_transactions": pd.read_csv("examples/gigler/data/gigler_transactions_2024_q1.csv"),
    "public.gig_prices": pd.read_csv("examples/gigler/data/gig_prices_2024_q1.csv"),
    "public.marketing_campaigns": pd.read_csv("examples/gigler/data/marketing_campaigns_2024_q1.csv"),
    "public.gig_vendor_stats": pd.read_csv("examples/gigler/data/gig_vendor_stats_2024_q1.csv"),
})
```

The key format is `"schema_name.table_name"` — matching the `schema_name` and `table_name` on your `Check`.

---

## PostgresAdapter

Connects to a live PostgreSQL database.

```python
from dqt.adapters.postgres import PostgresAdapter

adapter = PostgresAdapter(
    host="localhost",
    port=5432,
    database="gigler_prod",
    user="dqt_readonly",
    password="...",
)

# Verify connectivity before running checks
health = adapter.health_check()
print(health.ok, health.latency_ms)
```

Using a connection string:

```python
adapter = PostgresAdapter.from_url(
    "postgresql://dqt_readonly:password@localhost:5432/gigler_prod"
)
```

---

## WarehouseAdapter protocol

All adapters implement:

```python
class WarehouseAdapter(Protocol):
    def health_check(self) -> HealthCheckResult: ...

    def sample(
        self,
        schema: str,
        table: str,
        n: int = 100_000,
        scope: CheckScope | None = None,
        filters: list[CheckFilter] | None = None,
        sampling_pct: float | None = None,
    ) -> pd.DataFrame: ...

    def aggregate(
        self,
        schema: str,
        table: str,
        exprs: list[AggExpr],
    ) -> dict[str, object]: ...

    def describe_columns(self, schema: str, table: str) -> list[ColumnMeta]: ...
    def list_schemas(self) -> list[str]: ...
    def list_tables(self, schema: str) -> list[str]: ...
```

### HealthCheckResult

```python
health = adapter.health_check()
health.ok           # bool
health.latency_ms   # float
health.detail       # str — error message if not ok
```

### describe_columns

```python
cols = adapter.describe_columns("public", "gigler_transactions")
for col in cols:
    print(col.name, col.dtype, col.nullable)
```

### list_schemas / list_tables

```python
schemas = adapter.list_schemas()
tables = adapter.list_tables("public")
```

---

## Building a custom adapter

Implement the `WarehouseAdapter` protocol for any source:

```python
import pandas as pd
from dqt import WarehouseAdapter, AggExpr, ColumnMeta, HealthCheckResult, CheckScope, CheckFilter

class MyAdapter:
    def health_check(self) -> HealthCheckResult:
        return HealthCheckResult(ok=True, latency_ms=0.0, detail="")

    def sample(self, schema, table, n=100_000, scope=None, filters=None, sampling_pct=None) -> pd.DataFrame:
        # return a DataFrame of up to n rows
        ...

    def aggregate(self, schema, table, exprs: list[AggExpr]) -> dict:
        # execute each expr.sql as a SQL aggregate, return {expr.name: value}
        ...

    def describe_columns(self, schema, table) -> list[ColumnMeta]:
        ...

    def list_schemas(self) -> list[str]:
        ...

    def list_tables(self, schema) -> list[str]:
        ...
```
