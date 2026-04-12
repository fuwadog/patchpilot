.PHONY: lint typecheck security test format

# Install development dependencies
install-dev:
	pip install -r requirements-dev.txt

# Run all linters
lint:
	ruff .
	# Also run flake8 if preferred
	# flake8 .

# Run type checking
typecheck:
	mypy .

# Run security checks
security:
	bandit -r .
	safety check

# Run tests (if any)
test:
	pytest --cov=.

# Format code
format:
	black .
	isort .

# Run all checks in CI/CD
ci: install-dev lint typecheck security test

# Clean up
clean:
	find . -type d -name __pycache__ -exec rm -r {} +
	find . -type f -name .coverage -delete
	find . -type f -name .mypy_cache -delete
	find . -type f -name .ruff_cache -delete