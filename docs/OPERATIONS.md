# Operations guide

## First run

1. Copy `.env.example` to `.env` and set strong dashboard passwords.
2. Run `make up` to start PostgreSQL and the dashboard.
3. Run `make refresh` to generate demo exports, load them, build the reporting models, run checks, and calculate the experiment.
4. Open <http://localhost:8501> and sign in.
5. Run `make airflow` to enable the daily scheduled refresh. The DAG is created unpaused.

The first Docker build downloads Python packages and can take several minutes. Later builds reuse cached layers.

## Routine refresh

`make refresh` is safe to rerun. Unchanged exports insert zero rows while dbt and quality checks run again. To ingest new records, place updated CSVs in `data/generated/` with the same headers and a later `source_updated_at` for each new or corrected row. The loader does not treat a missing row as a deletion.

To use another export directory from host Python, set `PULSE_DATA_DIR` and run `python -m pulsemetrics.pipeline`. For Docker, update the corresponding volume mount in `docker-compose.yml`.

## Check the system

```bash
docker compose --profile orchestration ps
docker compose --profile orchestration logs --tail=100 airflow
docker compose --profile orchestration exec -T airflow airflow dags list-runs -d pulsemetrics_refresh
docker compose exec -T postgres pg_isready -U pulse -d pulsemetrics
```

The dashboard serves on `127.0.0.1:8501`; PostgreSQL serves on `127.0.0.1:5432`. Airflow's web interface is not exposed by this local profile. The command line shows DAG state and logs.

## When a refresh fails

1. Check the Airflow run and task logs. The task runs the same code as `make refresh`.
2. If ingestion failed, verify CSV headers, timestamp format, primary keys, and database health. Correct the file and rerun.
3. If dbt failed, run `dbt run --profiles-dir .` and `dbt test --profiles-dir .` from a configured host environment to see the exact model or test.
4. If freshness failed, confirm that source exports actually contain recent source records. Repeating a stale export does not make its source timestamp current.
5. If the experiment failed, confirm both control and treatment have at least two mature trial users.

Set `PULSE_ALERT_WEBHOOK` in `.env` for a compatible incoming webhook. Airflow will post a failure message after task retries are exhausted. Keep the webhook URL private.

## Data and credentials

Docker uses a named PostgreSQL volume. `make down` stops containers without deleting that volume. The `.env` file, source exports, logs, and Python environment are ignored by Git. See [security](SECURITY.md) before exposing any part of this stack outside a development machine.
