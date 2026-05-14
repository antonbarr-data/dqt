#!/usr/bin/env python3
"""
Load Gigler CSV data into ClickHouse on Railway.

Setup (Windows PowerShell):
    pip install clickhouse-connect pandas
    $env:CLICKHOUSE_PASSWORD = "<password from Railway Variables tab>"

Run:
    python load_gigler.py

Re-running is safe: each table is dropped and recreated before loading.
"""

import os
import sys
from pathlib import Path

import pandas as pd
import clickhouse_connect

# --- Connection ---------------------------------------------------------
HOST     = os.environ.get('CLICKHOUSE_HOST',
                          'clickhouse-production-bfdb.up.railway.app')
PORT     = int(os.environ.get('CLICKHOUSE_PORT', '443'))
USER     = os.environ.get('CLICKHOUSE_USER', 'default')
PASSWORD = os.environ.get('CLICKHOUSE_PASSWORD')

if not PASSWORD:
    sys.exit('Set CLICKHOUSE_PASSWORD env var (Railway → ClickHouse → Variables).')

client = clickhouse_connect.get_client(
    host=HOST, port=PORT, username=USER, password=PASSWORD, secure=True
)

# --- Data ---------------------------------------------------------------
DATA_DIR = Path(r'c:\anton\dqt\examples\gigler\data')

TABLES = {
    'marketing_campaigns': 'marketing_campaigns_*.csv',
    'gigler_transactions': 'gigler_transactions_*.csv',
    'gig_vendor_stats':    'gig_vendor_stats_*.csv',
    'gig_prices':          'gig_prices_*.csv',
}

# --- Helpers ------------------------------------------------------------
def infer_ch_type(series: pd.Series) -> str:
    """Map a pandas Series to a sensible ClickHouse type."""
    s = series.dropna()
    if s.empty:
        return 'String'
    dt = s.dtype
    if pd.api.types.is_bool_dtype(dt):
        return 'UInt8'
    if pd.api.types.is_integer_dtype(dt):
        return 'Int64'
    if pd.api.types.is_float_dtype(dt):
        return 'Float64'
    if pd.api.types.is_datetime64_any_dtype(dt):
        return 'DateTime64(3)'
    # Try string-as-datetime
    try:
        pd.to_datetime(s.head(200), errors='raise')
        return 'DateTime64(3)'
    except (ValueError, TypeError):
        pass
    return 'String'


def safe_col(name: str) -> str:
    return name.strip().replace(' ', '_').replace('-', '_')


# --- Main ---------------------------------------------------------------
for table_name, pattern in TABLES.items():
    files = sorted(DATA_DIR.glob(pattern))
    if not files:
        print(f'[skip] no files matched {pattern}')
        continue

    print(f'\n=== {table_name}  ({len(files)} files) ===')

    # Infer schema from the first file's first 5,000 rows
    sample = pd.read_csv(files[0], nrows=5000)
    col_types = {safe_col(c): infer_ch_type(sample[c]) for c in sample.columns}
    cols_ddl  = [f'`{c}` Nullable({t})' for c, t in col_types.items()]

    client.command(f'DROP TABLE IF EXISTS {table_name}')
    client.command(f"""
        CREATE TABLE {table_name} (
            {', '.join(cols_ddl)}
        ) ENGINE = MergeTree
        ORDER BY tuple()
    """)
    print('  schema:')
    for c, t in col_types.items():
        print(f'    {c:<40} {t}')

    # Load every quarter
    total = 0
    for f in files:
        df = pd.read_csv(f)
        df.columns = [safe_col(c) for c in df.columns]
        # Coerce any column we typed as datetime
        for c, t in col_types.items():
            if t == 'DateTime64(3)' and c in df.columns:
                df[c] = pd.to_datetime(df[c], errors='coerce')
        client.insert_df(table_name, df)
        total += len(df)
        print(f'  + {f.name:<45} {len(df):>10,} rows')

    actual = client.query(f'SELECT count() FROM {table_name}').result_rows[0][0]
    print(f'  total: {actual:,} rows')

print('\nDone.')
