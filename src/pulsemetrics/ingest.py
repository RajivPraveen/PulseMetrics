"""Transactional, watermark-based ingestion of source CSV exports into PostgreSQL."""
from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg import sql

TABLE_KEYS = {
    "customers": "customer_id", "web_visits": "visit_id",
    "subscription_periods": "period_id", "invoices": "invoice_id",
    "product_events": "event_id", "marketing_spend": "spend_id",
    "support_tickets": "ticket_id",
}


def initialize(conn: psycopg.Connection) -> None:
    schema = Path(__file__).resolve().parents[2] / "sql" / "001_raw.sql"
    conn.execute(schema.read_text())


def ingest(directory: Path, database_url: str) -> dict[str, int]:
    results = {}
    with psycopg.connect(database_url) as conn:
        initialize(conn)
        conn.commit()
        for table, key in TABLE_KEYS.items():
            path = directory / f"{table}.csv"
            if not path.exists():
                raise FileNotFoundError(path)
            with conn.transaction():
                watermark = conn.execute(
                    "SELECT watermark FROM control.ingestion_state WHERE source_name = %s FOR UPDATE",
                    (table,),
                ).fetchone()
                with path.open(newline="") as handle:
                    reader = csv.DictReader(handle)
                    columns = reader.fieldnames or []
                    if not columns or key not in columns or "source_updated_at" not in columns:
                        raise ValueError(f"Invalid source export: {path}")
                    rows = [
                        tuple(row[column] or None for column in columns)
                        for row in reader
                        if watermark is None or row["source_updated_at"] > watermark[0].isoformat()
                    ]
                if rows:
                    assignments = sql.SQL(", ").join(
                        sql.SQL("{} = EXCLUDED.{}").format(sql.Identifier(col), sql.Identifier(col))
                        for col in columns if col != key
                    )
                    statement = sql.SQL(
                        "INSERT INTO raw.{} ({}) VALUES ({}) ON CONFLICT ({}) DO UPDATE SET {} "
                        "WHERE EXCLUDED.source_updated_at >= raw.{}.source_updated_at"
                    ).format(
                        sql.Identifier(table),
                        sql.SQL(", ").join(map(sql.Identifier, columns)),
                        sql.SQL(", ").join(sql.Placeholder() for _ in columns),
                        sql.Identifier(key), assignments, sql.Identifier(table),
                    )
                    with conn.cursor() as cur:
                        cur.executemany(statement, rows)
                    latest = max(row[columns.index("source_updated_at")] for row in rows)
                    conn.execute(
                        "INSERT INTO control.ingestion_state(source_name, watermark, row_count) "
                        "VALUES (%s, %s, %s) ON CONFLICT (source_name) DO UPDATE SET "
                        "watermark = EXCLUDED.watermark, loaded_at = now(), "
                        "row_count = control.ingestion_state.row_count + EXCLUDED.row_count",
                        (table, latest, len(rows)),
                    )
                else:
                    conn.execute(
                        "UPDATE control.ingestion_state SET loaded_at = now() WHERE source_name = %s",
                        (table,),
                    )
                results[table] = len(rows)
    return results


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=Path("data/generated"))
    args = parser.parse_args()
    print(ingest(args.directory, os.environ["DATABASE_URL"]))


if __name__ == "__main__":
    main()
