#!/usr/bin/env python3
"""Load combined CSV files into BigQuery -- one table per CSV.

Reads the combined CSVs produced by combine_csv.py (files without quarterly
suffixes like _2024_q1) and loads each one into a BigQuery table, creating
the dataset and tables if they don't exist.

Usage:
    python examples/gigler/load_to_bigquery.py \
        --credentials examples/gigler/application_default_credentials.json \
        --project my-gcp-project

    # Custom dataset name (default: gigler):
    python examples/gigler/load_to_bigquery.py \
        --credentials examples/gigler/application_default_credentials.json \
        --project my-gcp-project \
        --dataset gigler_staging

Requires:
    pip install google-cloud-bigquery
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"

# Files whose stem matches this pattern are quarterly shards -- skip them.
_SHARD_RE = re.compile(r"_\d{4}_q\d$", re.IGNORECASE)


def is_combined(path: Path) -> bool:
    return not _SHARD_RE.search(path.stem)


def read_project_from_credentials(credentials_path: str) -> str | None:
    import json
    with open(credentials_path) as f:
        return json.load(f).get("quota_project_id")


def load(credentials_path: str, project: str, dataset_name: str) -> None:
    try:
        import google.auth
        from google.cloud import bigquery
        from google.cloud.exceptions import NotFound
    except ImportError:
        sys.exit("Missing dependency -- run: pip install google-cloud-bigquery")

    credentials, _ = google.auth.load_credentials_from_file(
        credentials_path,
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    client = bigquery.Client(credentials=credentials, project=project)

    # Create dataset if it doesn't exist
    dataset_ref = bigquery.Dataset(f"{project}.{dataset_name}")
    dataset_ref.location = "US"
    try:
        client.get_dataset(dataset_ref)
        print(f"  dataset {project}.{dataset_name} already exists")
    except NotFound:
        client.create_dataset(dataset_ref)
        print(f"  created dataset {project}.{dataset_name}")

    csvs = sorted(f for f in DATA_DIR.glob("*.csv") if is_combined(f))
    if not csvs:
        sys.exit(f"No combined CSV files found in {DATA_DIR}. Run combine_csv.py first.")

    for csv_path in csvs:
        table_id = f"{project}.{dataset_name}.{csv_path.stem}"
        print(f"\n  loading {csv_path.name} -> {table_id}")

        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.CSV,
            skip_leading_rows=1,
            autodetect=True,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        )

        with csv_path.open("rb") as f:
            job = client.load_table_from_file(f, table_id, job_config=job_config)

        job.result()  # wait for completion

        table = client.get_table(table_id)
        print(f"    {table.num_rows:,} rows  {len(table.schema)} columns")
        for field in table.schema:
            print(f"      {field.name:<40} {field.field_type}")

    print("\nDone.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Load Gigler CSVs into BigQuery")
    parser.add_argument(
        "--credentials", required=True,
        help="Path to application_default_credentials.json or service account JSON",
    )
    parser.add_argument("--project", default=None, help="GCP project ID (default: quota_project_id from credentials)")
    parser.add_argument("--dataset", default="gigler", help="BigQuery dataset name (default: gigler)")
    args = parser.parse_args()

    creds = Path(args.credentials)
    if not creds.exists():
        sys.exit(f"Credentials file not found: {creds}")

    project = args.project or read_project_from_credentials(str(creds))
    if not project:
        sys.exit("Could not determine project ID -- pass --project or add quota_project_id to credentials")

    load(str(creds), project, args.dataset)


if __name__ == "__main__":
    main()
