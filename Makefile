.PHONY: up refresh airflow test lint previews down

up:
	docker compose up -d postgres dashboard

refresh:
	docker compose --profile jobs run --rm refresh

airflow:
	docker compose --profile orchestration up -d airflow

test:
	pytest -q
	dbt test --profiles-dir .

lint:
	ruff check src tests dashboard dags scripts

previews:
	python scripts/generate_readme_assets.py

down:
	docker compose --profile orchestration down
