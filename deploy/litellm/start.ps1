# Runs the LiteLLM proxy on 127.0.0.1:4000 with LocalPilot's route file. Stops when the step is stopped.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$tools = if ($env:LOCALPILOT_TOOLS_DIR) { $env:LOCALPILOT_TOOLS_DIR } else { 'E:\LocalPilot\tools' }
$exe = Join-Path $tools 'litellm\Scripts\litellm.exe'
if (-not (Test-Path $exe)) { throw 'LiteLLM is not installed. Run deploy/litellm/install.ps1 first.' }
$env:LITELLM_TELEMETRY = 'False'
$env:PYTHONIOENCODING = 'utf-8'
& $exe --config (Join-Path $PSScriptRoot 'config.yaml') --host 127.0.0.1 --port 4000
exit $LASTEXITCODE
