# Shows the recorded target's state, address, uptime and cost so far. -Wait blocks until setup has finished.
param([switch]$Wait, [ValidateRange(30, 1800)][int]$TimeoutSeconds = 600)
. (Join-Path $PSScriptRoot 'common.ps1')

$state = Get-TrialState
if (-not $state) { Write-Output 'No trial target recorded. Run launch.ps1 first.'; exit 1 }
$i = (Invoke-Aws ec2 describe-instances --instance-ids $state.instance_id).Reservations[0].Instances[0]
$state.public_ip = $i.PublicIpAddress
Save-TrialState $state
Write-Output "Instance : $($state.instance_id) $($state.instance_type) $($i.State.Name)"
Write-Output "Address  : $(if ($i.PublicIpAddress) { $i.PublicIpAddress } else { 'none (stopped)' })"
if ($i.State.Name -eq 'running') {
    $hours = ((Get-Date).ToUniversalTime() - ([datetime]$i.LaunchTime).ToUniversalTime()).TotalHours
    Write-Output ("Running  : {0:N2} h since last start, about `${1:N3} so far at `${2}/h" -f $hours, ($hours * $state.hourly_usd), $state.hourly_usd)
}
if (-not $Wait -or $i.State.Name -ne 'running') { exit 0 }

$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
while ((Get-Date) -lt $deadline) {
    $r = & ssh -i $state.key_path -o BatchMode=yes -o ConnectTimeout=5 -o StrictHostKeyChecking=accept-new "$($state.ssh_user)@$($state.public_ip)" 'test -f /var/lib/localpilot/ready && ollama --version' 2>$null
    if ($LASTEXITCODE -eq 0) { Write-Output "Setup finished: $r"; exit 0 }
    Write-Output 'Waiting for setup (cloud-init installs Ollama and pulls the model)...'
    Start-Sleep -Seconds 20
}
throw "Setup did not finish within $TimeoutSeconds s. Check logs with: remote.ps1 -Action logs"
