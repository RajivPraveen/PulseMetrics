# Contributing

Thanks for improving PulseMetrics. Keep changes small enough to review and document any change to a metric definition.

1. Install Python 3.11+ and `pip install -e '.[dashboard,docs,dev]'`.
2. Run `ruff check src tests dashboard dags scripts` and `pytest -q`.
3. For model changes, run a local refresh and `dbt test --profiles-dir .` against PostgreSQL.
4. Update `docs/KPI_DEFINITIONS.md` and `docs/DATA_DICTIONARY.md` when a metric or column changes.
5. Regenerate preview images with `python scripts/generate_readme_assets.py` after visible dashboard data changes.

Do not commit `.env`, customer exports, logs, local databases, or build output. Preview images are generated from synthetic demo data only.
