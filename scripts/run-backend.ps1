$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Python = Join-Path $Backend ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
  Write-Host "Creating backend virtual environment..."
  python -m venv (Join-Path $Backend ".venv")
}

Write-Host "Installing backend dependencies..."
& $Python -m pip install -r (Join-Path $Backend "requirements.txt")

Push-Location $Backend
try {
  Write-Host "Applying migrations and loading demo data..."
  & $Python manage.py migrate
  & $Python manage.py seed_demo
  Write-Host "Backend running at http://127.0.0.1:8000"
  & $Python manage.py runserver 127.0.0.1:8000
}
finally {
  Pop-Location
}

