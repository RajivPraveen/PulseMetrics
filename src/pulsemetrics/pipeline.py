"""One-command refresh: generate demo sources, ingest, transform, test and analyze."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv

from pulsemetrics.experiments import analyze_warehouse
from pulsemetrics.generate import generate
from pulsemetrics.ingest import ingest

ROOT = Path(__file__).resolve().parents[2]


def check_freshness(database_url: str, max_hours: int = 48) -> None:
    with psycopg.connect(database_url) as conn:
        stale = conn.execute("""
            select source_name from control.ingestion_state
            where loaded_at < now() - (%s || ' hours')::interval
        """, (max_hours,)).fetchall()
        missing = conn.execute("select count(*) from control.ingestion_state").fetchone()[0]
    if stale or missing != 7:
        raise RuntimeError(f"Source freshness failed: stale={stale}, loaded_sources={missing}/7")


def run() -> None:
    load_dotenv(ROOT / ".env")
    data_dir = Path(os.getenv("PULSE_DATA_DIR", str(ROOT / "data/generated")))
    if not (data_dir / "customers.csv").exists():
        print("Generating synthetic source exports", flush=True)
        print(generate(data_dir), flush=True)
    database_url = os.environ["DATABASE_URL"]
    print("Ingested rows:", ingest(data_dir, database_url), flush=True)
    check_freshness(database_url)
    env = os.environ.copy()
    env.setdefault("DBT_PROFILES_DIR", str(ROOT))
    dbt = str(Path(sys.executable).with_name("dbt"))
    for command in ([dbt, "run"], [dbt, "test"], [dbt, "source", "freshness"]):
        subprocess.run(command, cwd=ROOT, env=env, check=True)
    print("Experiment:", analyze_warehouse(database_url), flush=True)


if __name__ == "__main__":
    run()
