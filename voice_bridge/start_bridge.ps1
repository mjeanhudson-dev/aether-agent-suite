# PowerShell launcher for Aether Voice Bridge
$ErrorActionPreference = "Stop"
$BridgeDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPython = Join-Path $BridgeDir ".venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Host "[!] Virtual environment not found at $VenvPython" -ForegroundColor Yellow
    Write-Host "[*] Creating virtual environment via uv..." -ForegroundColor Cyan
    uv venv (Join-Path $BridgeDir ".venv")
    uv pip install fastapi uvicorn pydantic httpx pytest --python $VenvPython
}

Write-Host "[*] Starting Aether Voice Bridge..." -ForegroundColor Green
& $VenvPython (Join-Path $BridgeDir "run_server.py")
