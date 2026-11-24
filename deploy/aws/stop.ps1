# Stops the trial instance: compute billing ends, the disk (and the downloaded models) stay and are billed per GB-month.
. (Join-Path $PSScriptRoot 'common.ps1')
$state = Get-TrialState
if (-not $state) { Write-Output 'No trial target recorded.'; exit 0 }
Invoke-Aws ec2 stop-instances --instance-ids $state.instance_id | Out-Null
Write-Output "Stopping $($state.instance_id)..."
& aws ec2 wait instance-stopped --region $Region --instance-ids $state.instance_id
$state.public_ip = $null
Save-TrialState $state
Write-Output ("Stopped. Disk still costs about `${0:N2}/month until you terminate." -f ($state.volume_gb * (Get-PriceTable)['ebs_gp3_gb_month']))
