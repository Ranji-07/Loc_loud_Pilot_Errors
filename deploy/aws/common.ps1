# Shared helpers for the LocalPilot AWS trial kit. Dot-source from the other scripts.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$script:Region   = if ($env:LOCALPILOT_AWS_REGION) { $env:LOCALPILOT_AWS_REGION } else { 'eu-north-1' }
$script:DataDir  = if ($env:LOCALPILOT_DATA_DIR) { $env:LOCALPILOT_DATA_DIR } else { 'E:\LocalPilot\data' }
$script:StateFile = Join-Path $script:DataDir 'aws\target.json'
$script:KeyName  = 'localpilot-trial'
$script:KeyPath  = Join-Path $HOME ".ssh\localpilot-trial-$($script:Region).pem"
$script:SgName   = 'localpilot-ssh'
$script:TagSpec  = @{ Key = 'LocalPilot'; Value = 'trial' }

$script:GpuTypes = @('g4dn.xlarge', 'g5.xlarge', 'g6.xlarge')
$script:AmiParams = @{
    cpu = '/aws/service/canonical/ubuntu/server/24.04/stable/current/amd64/hvm/ebs-gp3/ami-id'
    gpu = '/aws/service/deeplearning/ami/x86_64/base-oss-nvidia-driver-gpu-ubuntu-24.04/latest/ami-id'
}

function Invoke-Aws {
    # Runs the AWS CLI with the trial region and JSON output; throws with the CLI message on failure.
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$AwsArgs)
    $out = & aws @AwsArgs --region $script:Region --output json 2>&1
    if ($LASTEXITCODE -ne 0) { throw "aws $($AwsArgs[0..1] -join ' ') failed: $(($out | Out-String).Trim())" }
    $text = ($out | Out-String).Trim()
    if ($text) { return $text | ConvertFrom-Json }
}

function Get-TrialState {
    if (Test-Path $script:StateFile) { return Get-Content $script:StateFile -Raw | ConvertFrom-Json }
    return $null
}

function Save-TrialState($state) {
    New-Item -ItemType Directory -Force -Path (Split-Path $script:StateFile) | Out-Null
    $state | ConvertTo-Json -Depth 5 | Set-Content -Path $script:StateFile -Encoding utf8
}

function Get-MyPublicIp {
    $ip = (Invoke-RestMethod -Uri 'https://checkip.amazonaws.com' -TimeoutSec 10).Trim()
    if ($ip -notmatch '^\d{1,3}(\.\d{1,3}){3}$') { throw "Could not determine your public IPv4 address (got '$ip')" }
    return $ip
}

function Get-PriceTable {
    $file = Join-Path $PSScriptRoot '..\..\config\pricing.yaml'
    $prices = @{}
    $inRegion = $false
    foreach ($line in Get-Content $file) {
        if ($line -match "^\s{2}$([regex]::Escape($script:Region)):") { $inRegion = $true; continue }
        if ($inRegion -and $line -match '^\s{2}\S') { break }
        if ($inRegion -and $line -match '^\s{4,6}([a-z0-9._]+):\s*([0-9.]+)') { $prices[$Matches[1]] = [double]$Matches[2] }
    }
    return $prices
}

function Get-DefaultSubnet {
    $vpcs = Invoke-Aws ec2 describe-vpcs --filters 'Name=is-default,Values=true'
    if (-not $vpcs.Vpcs -or $vpcs.Vpcs.Count -eq 0) {
        throw "No default VPC in $($script:Region). Run step 'Create the default network' (deploy/aws/ensure-network.ps1) first."
    }
    $vpcId = $vpcs.Vpcs[0].VpcId
    $subnets = Invoke-Aws ec2 describe-subnets --filters "Name=vpc-id,Values=$vpcId" "Name=default-for-az,Values=true"
    if (-not $subnets.Subnets) { throw "Default VPC $vpcId has no default subnets." }
    return [pscustomobject]@{ VpcId = $vpcId; Subnets = @($subnets.Subnets | Sort-Object AvailabilityZone) }
}

function Write-Next([string[]]$lines) {
    Write-Output ''
    Write-Output 'Next:'
    $lines | ForEach-Object { Write-Output "  - $_" }
}
