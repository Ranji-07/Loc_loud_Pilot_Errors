# Runs one of a fixed set of commands on the trial instance over SSH. Arbitrary remote commands are not accepted.
param(
    [Parameter(Mandatory)][ValidateSet('status', 'gpu', 'models', 'pull-model', 'test', 'logs')][string]$Action,
    [ValidatePattern('^[A-Za-z0-9._:/-]+$')][string]$Model = 'qwen2.5:0.5b'
)
. (Join-Path $PSScriptRoot 'common.ps1')

$state = Get-TrialState
if (-not $state -or -not $state.public_ip) { throw 'No running target with a public IP.' }
$cmd = switch ($Action) {
    'status' { 'uptime; free -h | head -2; df -h / | tail -1; systemctl is-active ollama; echo idle-minutes=$(cat /var/lib/localpilot/idle-minutes 2>/dev/null)' }
    'gpu' { 'nvidia-smi || echo "No NVIDIA GPU on this instance type"' }
    'models' { 'ollama list; echo; ollama ps' }
    'pull-model' { "ollama pull $Model" }
    'test' { "curl -s http://127.0.0.1:11434/api/generate -d '{`"model`":`"$Model`",`"prompt`":`"Reply with one word: ready`",`"stream`":false}' | jq -r '.response, (`"tokens: `" + (.eval_count|tostring))'" }
    'logs' { 'sudo tail -n 60 /var/log/cloud-init-output.log; sudo journalctl -u ollama -n 20 --no-pager' }
}
& ssh -i $state.key_path -o BatchMode=yes -o ConnectTimeout=8 -o StrictHostKeyChecking=accept-new "$($state.ssh_user)@$($state.public_ip)" $cmd
exit $LASTEXITCODE
