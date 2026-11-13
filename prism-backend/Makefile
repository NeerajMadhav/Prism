.PHONY: dev worker beat test test-unit test-integration db-setup db-migrate lint typecheck

dev:
	uvicorn src.main:app --reload --port 8000

worker:
	celery -A src.workers.celery_app worker -l info

beat:
	celery -A src.workers.celery_app beat -l info

test:
	pytest -x tests/

test-unit:
	pytest tests/unit/

test-integration:
	pytest tests/integration/

db-setup:
	psql $(DATABASE_URL) -c "CREATE EXTENSION IF NOT EXISTS timescaledb;"

db-migrate:
	psql $(DATABASE_URL) -f src/db/schema.sql

lint:
	ruff check src/

typecheck:
	mypy src/ --strict
