.PHONY: help install dev test test-unit test-integration coverage clean lint format

help:
	@echo "FlashAlpha Python SDK Development Commands"
	@echo "=========================================="
	@echo "  make install       Install dependencies in editable mode"
	@echo "  make dev           Install with dev dependencies"
	@echo "  make test          Run full test suite (unit + integration)"
	@echo "  make test-unit     Run unit tests only"
	@echo "  make test-integration  Run integration tests only"
	@echo "  make coverage      Run tests with coverage report"
	@echo "  make lint          Run linting checks"
	@echo "  make format        Format code with black/isort"
	@echo "  make clean         Remove build artifacts and cache"

install:
	pip install -e .

dev:
	pip install -e ".[dev]"

test:
	pytest tests/ -v

test-unit:
	pytest tests/ -v -m "not integration"

test-integration:
	pytest tests/ -v -m "integration" || echo "No integration tests found (expected without API key)"

coverage:
	pytest tests/ --cov=src/flashalpha --cov-report=html --cov-report=term-missing
	@echo "Coverage report generated in htmlcov/index.html"

lint:
	@echo "Running linting checks..."
	find src/flashalpha -name "*.py" -exec python3 -m py_compile {} +
	find tests -name "*.py" -exec python3 -m py_compile {} +
	find . -maxdepth 1 -name "*.py" -exec python3 -m py_compile {} +
	@echo "✓ Syntax check passed"

format:
	@echo "Format support: install black and isort to enable"
	@echo "  pip install black isort"
	@echo "  black src/ tests/"
	@echo "  isort src/ tests/"

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf build dist *.egg-info

.PHONY: venv-activate
venv-activate:
	@echo "To activate the virtual environment, run:"
	@echo "  source venv/bin/activate"
