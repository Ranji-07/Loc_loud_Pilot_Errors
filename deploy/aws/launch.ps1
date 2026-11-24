# Launches one LocalPilot trial instance with Ollama bound to localhost, SSH open only to your IP,
# an encrypted gp3 disk and an idle auto-shutdown. Writes the target to the LocalPilot data dir.
param(
    [ValidateSet('t3.medium', 't3.large', 'g4dn.xlarge', 'g5.xlarge', 'g6.xlarge')]
    [string]$InstanceType = 't3.medium',
    [ValidateRange(8, 500)][int]$VolumeGb = 0,
    [ValidateRange(10, 720)][int]$IdleMinutes = 30,
    [ValidatePattern('^[A-Za-z0-9._:/-]*$')][string]$Model = 'qwen2.5:0.5b',
    [switch]$DryRun
)
. (Join-Path $PSScriptRoot 'common.ps1')

$isGpu = $GpuTypes -contains $InstanceType
$ami = (Invoke-Aws ssm get-parameter --name $(if ($isGpu) { $AmiParams.gpu } else { $AmiParams.cpu })).Parameter.Value
$img = (Invoke-Aws ec2 describe-images --image-ids $ami).Images[0]
$minDisk = [int]$img.BlockDeviceMappings[0].Ebs.VolumeSize
if ($VolumeGb -eq 0) { $VolumeGb = [Math]::Max($minDisk, $(if ($isGpu) { 80 } else { 30 })) }
if ($VolumeGb -lt $minDisk) { throw "The image needs at least $minDisk GB; got -VolumeGb $VolumeGb" }

$prices = Get-PriceTable
$hourly = $prices[$InstanceType]
Write-Output "Plan: $InstanceType ($(if ($isGpu) {'GPU'} else {'CPU'})) in $Region, image $($img.Name)"
Write-Output ("Cost: about `${0}/hour while running; disk {1} GB gp3 about `${2:N2}/month until terminated" -f $hourly, $VolumeGb, ($VolumeGb * $prices['ebs_gp3_gb_month']))
Write-Output "Idle shutdown after $IdleMinutes minutes without SSH sessions or loaded models."

if ($isGpu) {
    $q = Invoke-Aws service-quotas get-service-quota --service-code ec2 --quota-code L-DB2E81BA
    if ($q.Quota.Value -lt 4) { throw "GPU quota is $($q.Quota.Value) vCPUs in $Region. Run request-gpu-quota.ps1 and wait for approval, or use -InstanceType t3.medium." }
}

$existing = Get-TrialState
if ($existing -and -not $DryRun) { throw "A target is already recorded ($($existing.instance_id)). Use start.ps1 / terminate.ps1 first." }

if ($DryRun) {
    $out = & aws ec2 run-instances --region $Region --dry-run --image-id $ami --instance-type $InstanceType --count 1 2>&1 | Out-String
    if ($out -match 'DryRunOperation') { Write-Output 'Dry run: AWS confirms you are allowed to launch this instance. Nothing was created.'; exit 0 }
    if ($out -match 'VPCIdNotSpecified') { throw "No default VPC in $Region yet. Run step 'Create the default network' (deploy/aws/ensure-network.ps1), then dry-run again. Nothing was created." }
    throw "Dry run failed: $($out.Trim())"
}

$net = Get-DefaultSubnet

# Key pair: the private key only ever lives in ~/.ssh on this machine.
$keys = Invoke-Aws ec2 describe-key-pairs --filters "Name=key-name,Values=$KeyName"
if (-not $keys.KeyPairs) {
    New-Item -ItemType Directory -Force -Path (Split-Path $KeyPath) | Out-Null
    $material = & aws ec2 create-key-pair --region $Region --key-name $KeyName --key-type ed25519 --query KeyMaterial --output text
    if ($LASTEXITCODE -ne 0) { throw 'create-key-pair failed' }
    Set-Content -Path $KeyPath -Value $material -Encoding ascii -NoNewline
    Add-Content -Path $KeyPath -Value "`n" -Encoding ascii -NoNewline
    & icacls $KeyPath /inheritance:r /grant:r "$($env:USERNAME):(R)" | Out-Null
    Write-Output "Created key pair $KeyName, private key saved to $KeyPath"
} elseif (-not (Test-Path $KeyPath)) {
    throw "Key pair $KeyName exists in AWS but $KeyPath is missing. Delete the key pair in the EC2 console or restore the file."
}

$sgs = Invoke-Aws ec2 describe-security-groups --filters "Name=group-name,Values=$SgName" "Name=vpc-id,Values=$($net.VpcId)"
if ($sgs.SecurityGroups) { $sgId = $sgs.SecurityGroups[0].GroupId }
else {
    $sgId = (Invoke-Aws ec2 create-security-group --group-name $SgName --description 'LocalPilot trial: SSH from owner IP only' --vpc-id $net.VpcId).GroupId
    Write-Output "Created security group $sgId"
}
$myIp = Get-MyPublicIp
& aws ec2 authorize-security-group-ingress --region $Region --group-id $sgId --protocol tcp --port 22 --cidr "$myIp/32" 2>&1 | Out-Null
Write-Output "SSH allowed only from $myIp/32"

$tmp = New-Item -ItemType Directory -Force -Path (Join-Path $DataDir 'aws\tmp')
$userData = (Get-Content (Join-Path $PSScriptRoot 'user-data.sh') -Raw).Replace('__IDLE_MINUTES__', "$IdleMinutes").Replace('__MODEL__', $Model)
$udFile = Join-Path $tmp 'user-data.sh'
[IO.File]::WriteAllText($udFile, $userData.Replace("`r`n", "`n"))
$bdm = @(@{ DeviceName = $img.RootDeviceName; Ebs = @{ VolumeSize = $VolumeGb; VolumeType = 'gp3'; Encrypted = $true; DeleteOnTermination = $true } })
$bdmFile = Join-Path $tmp 'bdm.json'; ConvertTo-Json -InputObject $bdm -Depth 5 | Set-Content $bdmFile -Encoding ascii
$tags = @('instance', 'volume') | ForEach-Object { @{ ResourceType = $_; Tags = @(@{ Key = 'Name'; Value = 'localpilot-trial' }, $TagSpec) } }
$tagFile = Join-Path $tmp 'tags.json'; ConvertTo-Json -InputObject @($tags) -Depth 6 | Set-Content $tagFile -Encoding ascii

$launched = $null
foreach ($subnet in $net.Subnets) {
    try {
        $launched = Invoke-Aws ec2 run-instances --image-id $ami --instance-type $InstanceType --count 1 `
            --key-name $KeyName --security-group-ids $sgId --subnet-id $subnet.SubnetId --associate-public-ip-address `
            --block-device-mappings "file://$bdmFile" --tag-specifications "file://$tagFile" `
            --metadata-options 'HttpTokens=required,HttpEndpoint=enabled' `
            --instance-initiated-shutdown-behavior stop --user-data "file://$udFile"
        break
    } catch {
        if ($_.Exception.Message -match 'InsufficientInstanceCapacity|Unsupported') { Write-Output "No capacity in $($subnet.AvailabilityZone), trying next zone"; continue }
        throw
    }
}
if (-not $launched) { throw "No zone in $Region had capacity for $InstanceType right now." }

$iid = $launched.Instances[0].InstanceId
Write-Output "Launched $iid, waiting until it is running..."
& aws ec2 wait instance-running --region $Region --instance-ids $iid
$desc = (Invoke-Aws ec2 describe-instances --instance-ids $iid).Reservations[0].Instances[0]

Save-TrialState ([ordered]@{
    instance_id = $iid; instance_type = $InstanceType; region = $Region; public_ip = $desc.PublicIpAddress
    ssh_user = 'ubuntu'; key_path = $KeyPath; key_name = $KeyName; security_group_id = $sgId
    hourly_usd = $hourly; volume_gb = $VolumeGb; idle_minutes = $IdleMinutes; model = $Model
    launched_at = (Get-Date).ToUniversalTime().ToString('o')
})
Write-Output "Running at $($desc.PublicIpAddress). Target saved to $StateFile"
Write-Next @('Wait 3-6 minutes for setup, then run status.ps1 -Wait', 'Open the SSH tunnel (tunnel.ps1)', 'Stop the instance when you finish (stop.ps1)')
