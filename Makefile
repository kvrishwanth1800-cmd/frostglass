.PHONY: dev test lint format typecheck

dev:
	docker compose up --build

test:
	pytest

lint:
	ruff check .
	ruff format --check .

typecheck:
	mypy

format:
	ruff format .
