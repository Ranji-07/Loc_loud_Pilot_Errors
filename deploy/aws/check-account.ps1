# Read-only: shows what the AWS trial needs and what is missing. Creates nothing.
. (Join-Path $PSScriptRoot 'common.ps1')

$id = Invoke-Aws sts get-caller-identity
Write-Output "Signed in as : $(($id.Arn -split ':',6)[-1])"
Write-Output "Region       : $Region"

$quotas = @{ 'L-DB2E81BA' = 'On-demand G/VT vCPUs'; 'L-3819A6DF' = 'Spot G/VT vCPUs'; 'L-1216C47A' = 'On-demand standard vCPUs' }
foreach ($code in $quotas.Keys) {
    $q = Invoke-Aws service-quotas get-service-quota --service-code ec2 --quota-code $code
    Write-Output ("Quota        : {0,-26} = {1}" -f $quotas[$code], $q.Quota.Value)
}

$vpcs = Invoke-Aws ec2 describe-vpcs --filters 'Name=is-default,Values=true'
Write-Output ("Default VPC  : {0}" -f $(if ($vpcs.Vpcs.Count) { 'present' } else { 'MISSING (run ensure-network.ps1)' }))

$offer = Invoke-Aws ec2 describe-instance-type-offerings --location-type region --filters "Name=instance-type,Values=t3.medium,g4dn.xlarge,g5.xlarge,g6.xlarge"
Write-Output "Offered here : $(($offer.InstanceTypeOfferings.InstanceType | Sort-Object) -join ', ')"

$prices = Get-PriceTable
Write-Output "Prices (USD/h, pricing.yaml): $(($prices.GetEnumerator() | Sort-Object Value | ForEach-Object { "$($_.Key)=$($_.Value)" }) -join ', ')"

$state = Get-TrialState
if ($state) { Write-Output "Recorded target: $($state.instance_id) ($($state.instance_type))" } else { Write-Output 'Recorded target: none' }

$inst = Invoke-Aws ec2 describe-instances --filters 'Name=tag:LocalPilot,Values=*' "Name=instance-state-name,Values=pending,running,stopping,stopped"
$list = @($inst.Reservations | ForEach-Object { $_.Instances } | Where-Object { $_ })
Write-Output "LocalPilot instances: $($list.Count)"
$list | ForEach-Object { Write-Output "  $($_.InstanceId) $($_.InstanceType) $($_.State.Name)" }
