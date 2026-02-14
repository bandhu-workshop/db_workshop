# Format and type checking
check_format:
	@echo "Checking format..."
	uv run ruff check && uv tool run ruff format --check

check_type:
	@echo "Checking types..."
	uv run mypy --package workshop

format:
	@echo "Formatting code..."
	uv tool run ruff check --fix && uv tool run ruff format

seed00:
	@echo "Populating the database..."
	uv run python scripts/populate_db00.py

run00:
	@echo "Starting API server..."
	uv run python -m uvicorn workshop.00_personal_TODO.main:app --host 0.0.0.0 --port=8080 --reload