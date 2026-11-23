# Installs the LiteLLM proxy into its own virtual environment under the LocalPilot tools folder.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$tools = if ($env:LOCALPILOT_TOOLS_DIR) { $env:LOCALPILOT_TOOLS_DIR } else { 'E:\LocalPilot\tools' }
$venv = Join-Path $tools 'litellm'
$python = (Get-Command python -ErrorAction SilentlyContinue)?.Source
$candidates = @("$env:LOCALAPPDATA\Programs\Python\Python312\python.exe", "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe")
if (-not $python) { $python = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1 }
if (-not $python) { throw 'Python 3.11+ not found. Install Python, then re-run.' }
if (-not (Test-Path (Join-Path $venv 'Scripts\python.exe'))) { & $python -m venv $venv }
& (Join-Path $venv 'Scripts\python.exe') -m pip install --quiet --upgrade pip
& (Join-Path $venv 'Scripts\python.exe') -m pip install --quiet 'litellm[proxy]>=1.80,<2'
if ($LASTEXITCODE -ne 0) { throw 'pip install failed' }
& (Join-Path $venv 'Scripts\litellm.exe') --version
