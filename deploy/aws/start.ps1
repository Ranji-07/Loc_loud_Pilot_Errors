# Starts a stopped trial instance again and re-allows SSH from your current public IP (it may have changed).
. (Join-Path $PSScriptRoot 'common.ps1')
$state = Get-TrialState
if (-not $state) { throw 'No trial target recorded. Run launch.ps1 first.' }
Invoke-Aws ec2 start-instances --instance-ids $state.instance_id | Out-Null
& aws ec2 wait instance-running --region $Region --instance-ids $state.instance_id
$i = (Invoke-Aws ec2 describe-instances --instance-ids $state.instance_id).Reservations[0].Instances[0]
$state.public_ip = $i.PublicIpAddress
Save-TrialState $state
$myIp = Get-MyPublicIp
& aws ec2 authorize-security-group-ingress --region $Region --group-id $state.security_group_id --protocol tcp --port 22 --cidr "$myIp/32" 2>&1 | Out-Null
Write-Output "Running again at $($i.PublicIpAddress); SSH allowed from $myIp/32. Billing at `$$($state.hourly_usd)/h."
