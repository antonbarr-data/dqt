#!/usr/bin/env python3
"""Quick query helper for Gigler ClickHouse tables."""

import os
from pathlib import Path

import clickhouse_connect
import pandas as pd

_env_path = Path(__file__).parents[3] / '.env'
if _env_path.exists():
    for _line in _env_path.read_text(encoding='utf-8').splitlines():
        _line = _line.strip()
        if not _line or _line.startswith('#') or '=' not in _line:
            continue
        _k, _, _v = _line.partition('=')
        _k, _v = _k.strip(), _v.strip().strip('"').strip("'")
        os.environ.setdefault(_k, _v)

client = clickhouse_connect.get_client(
    host=os.environ.get('CLICKHOUSE_HOST', 'clickhouse-production-bfdb.up.railway.app'),
    port=int(os.environ.get('CLICKHOUSE_PORT', '443')),
    username=os.environ.get('CLICKHOUSE_USER', 'default'),
    password=os.environ.get('CLICKHOUSE_PASSWORD'),
    secure=True,
)

result = client.query('SELECT * FROM marketing_campaigns LIMIT 10')
df = pd.DataFrame(result.result_rows, columns=result.column_names)

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 200)
print(df.to_string(index=False))
