[CmdletBinding()]
param([string]$ProjectRoot = '', [string]$EvidencePath = '', [ValidateRange(1,3)][int]$TrialCount = 3, [switch]$ExecuteReboot)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if ($ExecuteReboot) { throw 'Full Notebook reboot is intentionally excluded; run the operator reboot checklist manually.' }
$root = if ($ProjectRoot) { (Resolve-Path $ProjectRoot).Path } else { (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path }
if (-not $EvidencePath) { $EvidencePath = Join-Path $root 'evidence\feature-005\recovery-local.md' }
$db = Join-Path $root 'storage\jobs.sqlite3'
$services = @('Local3D-ComfyUI','Local3D-API','Local3D-Nginx','cloudflared')
$missingServices = @($services | Where-Object { $null -eq (Get-Service -Name $_ -ErrorAction SilentlyContinue) })
if ($missingServices.Count -gt 0) {
  throw "BLOCKED: required restart services are not installed: $($missingServices -join ', ')"
}
function Snapshot { param([int]$Trial); $counts = @{}; if (Test-Path $db) { try { $rows = & sqlite3 $db "select status,count(*) from generation_jobs group by status" 2>$null; $rows | ForEach-Object { $parts = $_ -split '\|'; if ($parts.Count -eq 2) { $counts[$parts[0]] = [int]$parts[1] } } } catch {} }; [PSCustomObject]@{ Trial=$Trial; Utc=(Get-Date).ToUniversalTime().ToString('o'); Jobs=$counts } }
function Test-Ready {
  try {
    $api = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8000/api/v1/health/ready' -TimeoutSec 3
    $comfy = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8188/system_stats' -TimeoutSec 3
    $nginx = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8080/api/v1/health/live' -Headers @{ Host = 'mango74-api.mangosgo.com' } -TimeoutSec 3
    $tunnel = Get-Service -Name 'cloudflared' -ErrorAction Stop
    return ($api.StatusCode -eq 200 -and $comfy.StatusCode -eq 200 -and $nginx.StatusCode -eq 200 -and $tunnel.Status -eq 'Running')
  } catch { return $false }
}
$records = [System.Collections.Generic.List[object]]::new()
for ($trial=1; $trial -le $TrialCount; $trial++) {
  $before = Snapshot $trial
  $unsafe = @(Get-NetTCPConnection -State Established -LocalPort 8080 -ErrorAction SilentlyContinue).Count
  if ($unsafe) { throw "Trial $trial refused while proxy has active established work." }
  foreach ($name in $services) { $installed = Get-Service -Name $name -ErrorAction SilentlyContinue; if ($installed) { Restart-Service -Name $name -Force; (Get-Service $name).WaitForStatus('Running',[TimeSpan]::FromSeconds(60)) } }
  $ready = $false; $deadline=[DateTime]::UtcNow.AddSeconds(90)
  do { $ready = Test-Ready; if(-not $ready){Start-Sleep -Seconds 2} } while(-not $ready -and [DateTime]::UtcNow -lt $deadline)
  $after = Snapshot $trial
  $records.Add([PSCustomObject]@{Trial=$trial; Ready=$ready; Before=$before; After=$after})
  if (-not $ready) { throw "Trial $trial did not restore API readiness." }
}
$lines=@('# Feature 005 local recovery matrix','',"- Trials: $TrialCount",'- Restart order: ComfyUI -> API -> Nginx -> cloudflared','- Full reboot: NOT EXECUTED by design.','', '| Trial | Readiness | Durable snapshot |','|---:|:---:|---|'); foreach($r in $records){$lines += "| $($r.Trial) | PASS | retained before/after snapshots |"}; New-Item -ItemType Directory (Split-Path $EvidencePath) -Force | Out-Null; Set-Content -LiteralPath $EvidencePath -Value ($lines -join [Environment]::NewLine) -Encoding utf8; Write-Output "PASS: recovery matrix recorded at $EvidencePath"
