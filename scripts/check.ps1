# Luca — health check + tests
# Usage:  .\scripts\check.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

Write-Host "=== Luca Health Check ===" -ForegroundColor Cyan
python main.py --check
if ($LASTEXITCODE -ne 0) { Write-Host "HEALTH CHECK FAILED" -ForegroundColor Red; exit 1 }

Write-Host ""
Write-Host "=== Running tests ===" -ForegroundColor Cyan
python -m pytest tests/ -v
if ($LASTEXITCODE -ne 0) { Write-Host "TESTS FAILED" -ForegroundColor Red; exit 1 }

Write-Host "=== All checks passed ===" -ForegroundColor Green
