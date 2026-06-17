.PHONY: lint typecheck security test format clean

# Install development dependencies
install-dev:
	pip install -r requirements-dev.txt

# Run all linters
lint:
	ruff src/

# Run type checking
typecheck:
	mypy src/

# Run security checks
security:
	bandit -r src/
	safety check

# Run tests (if any)
test:
	pytest --cov=src/ --cov-report=term-missing

# Format code
format:
	black src/
	isort src/

# Run all checks in CI/CD
ci: lint typecheck security test

# Clean up
clean:
	@powershell -Command "Get-ChildItem -Path . -Directory -Name __pycache__ -Recurse | ForEach-Object { Remove-Item -LiteralPath $_ -Recurse -Force }"
	@powershell -Command "Remove-Item -LiteralPath .\.coverage -Force -ErrorAction SilentlyContinue"
	@powershell -Command "Remove-Item -LiteralPath .\.mypy_cache -Recurse -Force -ErrorAction SilentlyContinue"
	@powershell -Command "Remove-Item -LiteralPath .\.ruff_cache -Recurse -Force -ErrorAction SilentlyContinue"
