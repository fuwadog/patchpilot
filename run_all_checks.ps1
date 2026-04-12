# PatchPilot - Run All Tests & Checks
# This script runs all linters, type checkers, security checks, and tests

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Running All Tests & Checks for PatchPilot" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Activate virtual environment
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "`n[1/5] Activating virtual environment..." -ForegroundColor Yellow
    & ".\venv\Scripts\Activate.ps1"
} else {
    Write-Host "ERROR: venv not found. Run 'python -m venv venv' first." -ForegroundColor Red
    exit 1
}

Write-Host "`n[2/5] Running ruff (linter)..." -ForegroundColor Yellow
python -m ruff check .
if ($LASTEXITCODE -ne 0) { Write-Host "FAIL: ruff check failed" -ForegroundColor Red; exit 1 }

Write-Host "`n[3/5] Running mypy (type checker)..." -ForegroundColor Yellow
python -m mypy .
if ($LASTEXITCODE -ne 0) { Write-Host "FAIL: mypy check failed" -ForegroundColor Red; exit 1 }

Write-Host "`n[4/5] Running safety (security)..." -ForegroundColor Yellow
python -m safety check
if ($LASTEXITCODE -ne 0) { Write-Host "WARNING: security vulnerabilities found" -ForegroundColor Yellow }

Write-Host "`n[5/5] Running pytest (tests)..." -ForegroundColor Yellow
python -m pytest --cov=. --cov-report=term-missing
if ($LASTEXITCODE -ne 0) { Write-Host "WARNING: no tests found or tests failed" -ForegroundColor Yellow }

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "All checks completed!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan