#!/usr/bin/env python3
"""Combine per-quarter CSV shards into one file per table.

Usage (from repo root or this directory):
    python examples/gigler/combine_csv.py

Output files are written to examples/gigler/data/ alongside the source files,
e.g. marketing_campaigns.csv, gigler_transactions.csv, etc.
"""
from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"


def table_name(filename: str) -> str:
    """Strip trailing date/quarter suffixes to get the base table name.

    Examples:
      marketing_campaigns_2024_q1.csv -> marketing_campaigns
      gigler_transactions_2025_q1.csv -> gigler_transactions
    """
    stem = Path(filename).stem
    return re.sub(r"[_-]?\d{4}[_-]q\d$", "", stem, flags=re.IGNORECASE)


def main() -> None:
    shards: dict[str, list[Path]] = defaultdict(list)
    for f in sorted(DATA_DIR.glob("*.csv")):
        t = table_name(f.name)
        if t != f.stem:          # only files that actually have a suffix stripped
            shards[t].append(f)

    if not shards:
        print("No quarterly CSV shards found in", DATA_DIR)
        return

    for table, files in sorted(shards.items()):
        out = DATA_DIR / f"{table}.csv"
        header_written = False
        rows_written = 0
        with out.open("w", newline="", encoding="utf-8") as fout:
            writer = csv.writer(fout)
            for path in files:
                with path.open(newline="", encoding="utf-8") as fin:
                    reader = csv.reader(fin)
                    header = next(reader)
                    if not header_written:
                        writer.writerow(header)
                        header_written = True
                    for row in reader:
                        writer.writerow(row)
                        rows_written += 1
        print(f"  {out.name:<40} {rows_written:>6} rows  ({len(files)} shards)")


if __name__ == "__main__":
    main()
