param(
    [switch]$NoInstall
)

$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path "$PSScriptRoot\..").Path
Set-Location $ProjectRoot

if (-not (Test-Path ".venv")) {
    Write-Host "[1/5] Creating .venv" -ForegroundColor Cyan
    python -m venv .venv
}

$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

Write-Host "[2/5] Upgrading pip" -ForegroundColor Cyan
& $PythonExe -m pip install -U pip | Out-Null

if (-not $NoInstall) {
    Write-Host "[3/5] Installing dependencies" -ForegroundColor Cyan
    & $PythonExe -m pip install -r requirements.txt
} else {
    Write-Host "[3/5] Skipping dependencies (-NoInstall)" -ForegroundColor Yellow
}

$envExists = Test-Path ".env"
$exampleExists = Test-Path ".env.example"
if ((-not $envExists) -and $exampleExists) {
    Copy-Item ".env.example" ".env"
    Write-Host "[4/5] Created .env from .env.example" -ForegroundColor Green
} else {
    Write-Host "[4/5] .env exists, skipping" -ForegroundColor Yellow
}

New-Item -ItemType Directory -Path "data" -Force | Out-Null
New-Item -ItemType Directory -Path ".runtime" -Force | Out-Null

Write-Host "[5/5] Starting FastAPI and Streamlit" -ForegroundColor Cyan

$env:PYTHONPATH = $ProjectRoot

Start-Process -FilePath $PythonExe -ArgumentList "-m", "uvicorn", "app.api.main:app", "--host", "127.0.0.1", "--port", "8000" -WorkingDirectory $ProjectRoot -WindowStyle Hidden

Start-Process -FilePath $PythonExe -ArgumentList "-m", "streamlit", "run", "app/ui/main.py", "--server.port", "8501", "--server.headless", "true" -WorkingDirectory $ProjectRoot -WindowStyle Hidden

Write-Host "Started successfully:" -ForegroundColor Green
Write-Host "- API: http://127.0.0.1:8000/health"
Write-Host "- UI : http://127.0.0.1:8501"
