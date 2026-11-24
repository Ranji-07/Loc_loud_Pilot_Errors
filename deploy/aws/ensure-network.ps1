# Creates the AWS default VPC (VPC, one public subnet per zone, internet gateway) if the region has none.
# The default VPC itself is free. Safe to re-run.
. (Join-Path $PSScriptRoot 'common.ps1')

$vpcs = Invoke-Aws ec2 describe-vpcs --filters 'Name=is-default,Values=true'
if ($vpcs.Vpcs.Count) {
    Write-Output "Default VPC already exists in $Region ($($vpcs.Vpcs[0].VpcId)). Nothing to do."
    exit 0
}
$res = Invoke-Aws ec2 create-default-vpc
Write-Output "Created default VPC $($res.Vpc.VpcId) in $Region."
