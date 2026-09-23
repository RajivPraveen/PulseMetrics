"""Daily warehouse refresh. Failure callback sends a webhook if configured."""
from __future__ import annotations

import json
import os
import subprocess
from datetime import UTC, datetime, timedelta
from urllib.request import Request, urlopen

from airflow import DAG
from airflow.operators.python import PythonOperator


def refresh() -> None:
    subprocess.run([
        "/opt/airflow/pulsemetrics/.venv/bin/python", "-m", "pulsemetrics.pipeline"
    ], check=True)


def notify_failure(context: dict) -> None:
    webhook = os.getenv("PULSE_ALERT_WEBHOOK")
    if not webhook:
        return
    payload = json.dumps({
        "text": f"PulseMetrics refresh failed: {context['dag'].dag_id} "
                f"run={context['run_id']} task={context['task_instance'].task_id}"
    }).encode()
    request = Request(webhook, data=payload, headers={"Content-Type": "application/json"})
    with urlopen(request, timeout=10):
        pass


with DAG(
    "pulsemetrics_refresh",
    start_date=datetime(2026, 9, 1, tzinfo=UTC),
    schedule="0 6 * * *",
    catchup=False,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=10),
                  "on_failure_callback": notify_failure},
    tags=["saas", "analytics"],
) as dag:
    PythonOperator(task_id="refresh_warehouse", python_callable=refresh)
