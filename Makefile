.PHONY: help install dev lint test run clean

help:
	@echo "FREEDMENFINDER Development Tasks"
	@echo "=================================="
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  install       Install dependencies"
	@echo "  dev           Install dev dependencies"
	@echo "  lint          Run code linting"
	@echo "  test          Run tests"
	@echo "  run           Run the app locally"
	@echo "  run-demo      Run in demo mode"
	@echo "  clean         Remove cache and build files"
	@echo "  requirements  Generate requirements.txt from imports"

install:
	uv venv
	.venv\Scripts\activate && uv pip install -r requirements.txt

dev:
	uv pip install -r requirements-dev.txt

lint:
	black --check .
	flake8 . --max-line-length=100
	pylint **/*.py

test:
	pytest --cov=. --cov-report=html

run:
	.venv\Scripts\streamlit.exe run app.py

run-demo:
	set DEMO_MODE=True && .venv\Scripts\streamlit.exe run app.py

clean:
	rmdir /s /q __pycache__ .pytest_cache .coverage htmlcov
	find . -type d -name __pycache__ -exec rmdir /s /q {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete

requirements:
	uv pip freeze > requirements.txt
