# Terminates the trial instance and deletes its disk and security group. -DeleteKey also removes the key pair.
param([switch]$DeleteKey)
. (Join-Path $PSScriptRoot 'common.ps1')
$state = Get-TrialState
if (-not $state) { Write-Output 'No trial target recorded.'; exit 0 }
Invoke-Aws ec2 terminate-instances --instance-ids $state.instance_id | Out-Null
Write-Output "Terminating $($state.instance_id)..."
& aws ec2 wait instance-terminated --region $Region --instance-ids $state.instance_id
for ($i = 0; $i -lt 6; $i++) {
    & aws ec2 delete-security-group --region $Region --group-id $state.security_group_id 2>$null
    if ($LASTEXITCODE -eq 0) { Write-Output "Deleted security group $($state.security_group_id)"; break }
    Start-Sleep -Seconds 10
}
if ($DeleteKey) {
    & aws ec2 delete-key-pair --region $Region --key-name $state.key_name | Out-Null
    if (Test-Path $state.key_path) { Remove-Item $state.key_path -Force }
    Write-Output "Deleted key pair $($state.key_name) and $($state.key_path)"
}
Remove-Item $StateFile -Force
Write-Output 'Terminated. Nothing from the trial is billing any more (the default VPC is free).'
