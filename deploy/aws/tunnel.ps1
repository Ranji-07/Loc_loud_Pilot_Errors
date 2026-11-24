# Opens an SSH tunnel: http://127.0.0.1:<LocalPort> on this laptop -> Ollama on the instance (127.0.0.1:11434).
# Keeps running until you stop the step. While the tunnel is open, the idle shutdown treats the machine as in use.
param([ValidateRange(1024, 65535)][int]$LocalPort = 11435)
. (Join-Path $PSScriptRoot 'common.ps1')

$state = Get-TrialState
if (-not $state -or -not $state.public_ip) { throw 'No running target with a public IP. Run status.ps1 (or start.ps1).' }
Write-Output "Tunnel: http://127.0.0.1:$LocalPort -> $($state.public_ip):11434 (Ctrl+C or Stop to close)"
& ssh -i $state.key_path -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o StrictHostKeyChecking=accept-new `
    -L "127.0.0.1:${LocalPort}:127.0.0.1:11434" "$($state.ssh_user)@$($state.public_ip)"
exit $LASTEXITCODE
