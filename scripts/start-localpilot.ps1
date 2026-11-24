# Starts the LocalPilot backend (which also serves the dashboard) on http://127.0.0.1:8765.
# First run builds the dashboard if apps/web/dist is missing.
param([switch]$Rebuild, [switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$py = Join-Path $root 'backend\.venv\Scripts\python.exe'
if (-not (Test-Path $py)) {
    throw "Backend environment missing. Run: py -3.12 -m venv backend\.venv; backend\.venv\Scripts\python.exe -m pip install -e 'backend[dev]'"
}
$web = Join-Path $root 'apps\web'
if ($Rebuild -or -not (Test-Path (Join-Path $web 'dist\index.html'))) {
    Write-Output 'Building the dashboard (first run only)...'
    Push-Location $web
    try {
        if (-not (Test-Path node_modules)) { npm install --no-audit --no-fund; if ($LASTEXITCODE) { throw 'npm install failed' } }
        npm run build; if ($LASTEXITCODE) { throw 'dashboard build failed' }
    } finally { Pop-Location }
}
$busy = Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue
if ($busy) { Write-Output 'LocalPilot (or another program) already listens on port 8765.'; if (-not $NoBrowser) { Start-Process 'http://127.0.0.1:8765/' }; exit 0 }
if (-not $NoBrowser) {
    Start-Job { Start-Sleep 4; Start-Process 'http://127.0.0.1:8765/' } | Out-Null
}
Write-Output 'Starting LocalPilot on http://127.0.0.1:8765 (Ctrl+C to stop)'
Push-Location (Join-Path $root 'backend')
try { & $py -m localpilot } finally { Pop-Location }
