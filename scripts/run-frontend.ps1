$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Frontend = Join-Path $Root "frontend"
$LocalNpm = Join-Path $Root ".tools\node-v22.16.0-win-x64\npm.cmd"

if (Test-Path $LocalNpm) {
  $Npm = $LocalNpm
} else {
  $Npm = "npm"
}

Push-Location $Frontend
try {
  Write-Host "Installing frontend dependencies..."
  & $Npm install
  Write-Host "Frontend running at http://127.0.0.1:5173"
  & $Npm run dev -- --host 127.0.0.1 --port 5173
}
finally {
  Pop-Location
}

