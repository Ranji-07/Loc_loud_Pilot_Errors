# Quick usage check from the terminal.
#   ./scripts/check-usage.ps1            numbers + alerts (from the LocalPilot backend)
#   ./scripts/check-usage.ps1 -Summary   also asks the small local model for a plain-language summary
#   ./scripts/check-usage.ps1 -Offline   works without the backend (direct probes only)
param([switch]$Summary, [switch]$Offline, [string]$Region = 'eu-north-1')
$ErrorActionPreference = 'Stop'
$base = 'http://127.0.0.1:8765/api/v1'

if (-not $Offline) {
    try { $u = Invoke-RestMethod "$base/usage" -TimeoutSec 60 } catch { Write-Output "Backend not reachable ($($_.Exception.Message)); falling back to -Offline."; $Offline = $true }
}

if (-not $Offline) {
    $l = $u.local
    Write-Output ("Laptop   : CPU {0}%  RAM {1}% used ({2} GB free)" -f $l.cpu_percent, $l.ram_used_percent, $l.ram_available_gb)
    $l.disks | ForEach-Object { Write-Output ("Disk     : {0} {1} GB free of {2} GB" -f $_.mount, $_.free_gb, $_.total_gb) }
    Write-Output ("Ollama   : {0}; loaded: {1}" -f $(if ($u.ollama.reachable) { 'running' } else { 'not running' }), (($u.ollama.loaded | ForEach-Object name) -join ', '))
    if ($u.aws.available) {
        $n = @($u.aws.instances).Count
        Write-Output ("AWS      : {0} LocalPilot instance(s) in {1}" -f $n, $u.aws.region)
        $u.aws.instances | ForEach-Object { Write-Output ("           {0} {1} {2} `${3}/h, so far `${4}" -f $_.id, $_.type, $_.state, $_.hourly_usd, $_.cost_since_start_usd) }
    } else { Write-Output "AWS      : $($u.aws.reason)" }
    Write-Output 'Alerts   :'
    $u.alerts | ForEach-Object { Write-Output "  [$($_.level)] $($_.text)" }
    if ($Summary) {
        $s = Invoke-RestMethod -Method Post "$base/usage/$($u.id)/summary" -Headers @{ 'x-localpilot-client' = '1' } -TimeoutSec 180
        Write-Output "Summary ($($s.source) $($s.model)):"
        Write-Output $(if ($s.text) { $s.text } else { $s.error })
    }
    exit 0
}

$os = Get-CimInstance Win32_OperatingSystem
$ramPct = [Math]::Round(100 * (1 - $os.FreePhysicalMemory / $os.TotalVisibleMemorySize), 1)
$cpu = (Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average
Write-Output "Laptop   : CPU $cpu%  RAM $ramPct% used"
Get-PSDrive -PSProvider FileSystem | Where-Object Used | ForEach-Object { Write-Output ("Disk     : {0}: {1:N1} GB free" -f $_.Name, ($_.Free / 1GB)) }
if (Get-Command ollama -ErrorAction SilentlyContinue) { Write-Output 'Ollama loaded models:'; ollama ps }
if (Get-Command aws -ErrorAction SilentlyContinue) {
    Write-Output "AWS LocalPilot instances in ${Region}:"
    aws ec2 describe-instances --region $Region --filters 'Name=tag:LocalPilot,Values=*' 'Name=instance-state-name,Values=pending,running,stopping,stopped' `
        --query 'Reservations[].Instances[].[InstanceId,InstanceType,State.Name,LaunchTime]' --output table
}
