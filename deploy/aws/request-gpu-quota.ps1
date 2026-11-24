# Asks AWS to raise the on-demand G/VT vCPU quota so one GPU instance can start.
# g4dn.xlarge and g5.xlarge need 4 vCPUs. The request is free; AWS reviews it (hours to days).
param([ValidateRange(4, 64)][int]$Vcpus = 4)
. (Join-Path $PSScriptRoot 'common.ps1')

$q = Invoke-Aws service-quotas get-service-quota --service-code ec2 --quota-code L-DB2E81BA
Write-Output "Current on-demand G/VT quota: $($q.Quota.Value) vCPUs"
if ($q.Quota.Value -ge $Vcpus) { Write-Output 'Quota is already high enough.'; exit 0 }

$open = Invoke-Aws service-quotas list-requested-service-quota-change-history-by-quota --service-code ec2 --quota-code L-DB2E81BA
$pending = @($open.RequestedQuotas | Where-Object { $_.Status -in 'PENDING', 'CASE_OPENED' })
if ($pending.Count) { Write-Output "A request is already open: $($pending[0].Id) status $($pending[0].Status)"; exit 0 }

$r = Invoke-Aws service-quotas request-service-quota-increase --service-code ec2 --quota-code L-DB2E81BA --desired-value $Vcpus
Write-Output "Requested $Vcpus vCPUs. Request id $($r.RequestedQuota.Id), status $($r.RequestedQuota.Status)."
Write-Next @('Re-run check-account.ps1 later to see the new quota.', 'Meanwhile you can run the CPU trial with -InstanceType t3.medium.')
