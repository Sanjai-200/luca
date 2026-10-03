# Luca — run all tests
# Usage:  .\scripts\test.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..
Write-Host "=== Running Luca tests ===" -ForegroundColor Cyan
python -m pytest tests/ -v
if ($LASTEXITCODE -ne 0) { Write-Host "TESTS FAILED" -ForegroundColor Red; exit 1 }
Write-Host "=== All tests passed ===" -ForegroundColor Green
