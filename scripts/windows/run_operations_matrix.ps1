[CmdletBinding()]
param(
    [string]$ProjectRoot = '',
    [string]$EvidencePath = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if ([string]::IsNullOrWhiteSpace($ProjectRoot)) { $ProjectRoot = (Resolve-Path (Join-Path $scriptRoot '..\..')).Path }
if ([string]::IsNullOrWhiteSpace($EvidencePath)) { $EvidencePath = Join-Path $ProjectRoot 'evidence\feature-004\us4-operations.md' }
Set-Location -LiteralPath $ProjectRoot
$fatalLog = Join-Path $ProjectRoot 'output\operations-fatal.log'
New-Item -ItemType Directory -Path (Split-Path -Parent $fatalLog) -Force | Out-Null
Set-Content -LiteralPath $fatalLog -Value '' -Encoding utf8
trap {
    ($_ | Out-String).Trim() | Set-Content -LiteralPath $fatalLog -Encoding utf8
    break
}
$services = @('Local3D-ComfyUI', 'Local3D-API', 'Local3D-Web', 'Local3D-Caddy')
$checks = [System.Collections.Generic.List[object]]::new()
$db = Join-Path $ProjectRoot 'storage\jobs.sqlite3'
$storage = Join-Path $ProjectRoot 'storage'

function Add-Check([string]$Name, [bool]$Passed, [string]$Observed) {
    $script:checks.Add([PSCustomObject]@{ Name = $Name; Passed = $Passed; Observed = $Observed })
    if (-not $Passed) { throw "$Name failed: $Observed" }
}
function Wait-Running {
    param([string[]]$Names = $services, [int]$TimeoutSeconds = 120)
    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    do {
        $state = @(Get-Service -Name $Names -ErrorAction SilentlyContinue)
        if ($state.Count -eq $Names.Count -and @($state | Where-Object Status -ne 'Running').Count -eq 0) { return }
        Start-Sleep -Seconds 2
    } while ([DateTime]::UtcNow -lt $deadline)
    throw 'service stack did not return to Running within two minutes'
}
function HttpStatus([string]$Uri) {
    try { return [int](Invoke-WebRequest -UseBasicParsing -Uri $Uri -TimeoutSec 5).StatusCode }
    catch { if ($_.Exception.Response) { return [int]$_.Exception.Response.StatusCode }; return 0 }
}
function Start-Chain {
    foreach ($name in $services) { if ((Get-Service -Name $name).Status -ne 'Running') { Start-Service -Name $name } }
    Wait-Running
    $deadline = [DateTime]::UtcNow.AddSeconds(120)
    do {
        if ((HttpStatus 'http://127.0.0.1:8080/' -eq 200) -and
            (HttpStatus 'http://127.0.0.1:8080/api/v1/health/live' -eq 200) -and
            (HttpStatus 'http://127.0.0.1:8188/system_stats' -eq 200)) { return }
        Start-Sleep -Seconds 2
    } while ([DateTime]::UtcNow -lt $deadline)
    throw 'local HTTP chain did not recover within two minutes'
}
function Stop-One([string]$Name) {
    Stop-Service -Name $Name -Force
    $deadline = [DateTime]::UtcNow.AddSeconds(120)
    do { if ((Get-Service -Name $Name).Status -eq 'Stopped') { return }; Start-Sleep -Seconds 2 } while ([DateTime]::UtcNow -lt $deadline)
    throw "$Name did not stop within two minutes"
}

$beforeDb = if (Test-Path $db) { (Get-Item $db).Length } else { 0 }
$beforeStorage = Test-Path $storage
Add-Check 'installed-started-stack' ((@(Get-Service -Name $services -ErrorAction SilentlyContinue).Count -eq 4) -and @((Get-Service -Name $services) | Where-Object Status -ne 'Running').Count -eq 0) 'four approved services are installed and running'
Add-Check 'loopback-health-baseline' ((HttpStatus 'http://127.0.0.1:8080/' -eq 200) -and (HttpStatus 'http://127.0.0.1:8080/api/v1/health/live' -eq 200) -and (HttpStatus 'http://127.0.0.1:8188/system_stats' -eq 200)) 'Caddy web/API routes and ComfyUI respond'
Add-Check 'quick-tunnel-absent' (@(Get-Process cloudflared -ErrorAction SilentlyContinue).Count -eq 0) 'no Quick Tunnel process was used'

Stop-One 'Local3D-Caddy'
$caddyAfter = HttpStatus 'http://127.0.0.1:8080/'
$apiAfterCaddy = HttpStatus 'http://127.0.0.1:8000/api/v1/health/live'
Add-Check 'caddy-failure-diagnosis' (($caddyAfter -ne 200) -and ($apiAfterCaddy -eq 200)) "caddy=$caddyAfter; direct_api=$apiAfterCaddy"
Start-Chain

Stop-One 'Local3D-Web'
$webFailureRoot = HttpStatus 'http://127.0.0.1:8080/'
$webFailureDirectApi = HttpStatus 'http://127.0.0.1:8000/api/v1/health/live'
Add-Check 'web-failure-diagnosis' (($webFailureDirectApi -eq 200) -and ($webFailureRoot -ne 200)) "root_through_caddy=$webFailureRoot; direct_api=$webFailureDirectApi"
Start-Chain

Stop-One 'Local3D-API'
$apiFailureRoot = HttpStatus 'http://127.0.0.1:8080/'
$apiFailureDirectWeb = HttpStatus 'http://127.0.0.1:3000/'
$apiFailureDirectComfy = HttpStatus 'http://127.0.0.1:8188/system_stats'
Add-Check 'api-failure-diagnosis' (($apiFailureDirectWeb -ne 200) -and ($apiFailureDirectComfy -eq 200) -and ($apiFailureRoot -ne 200)) "root_through_caddy=$apiFailureRoot; direct_web=$apiFailureDirectWeb; direct_comfy=$apiFailureDirectComfy"
Start-Chain

Stop-One 'Local3D-ComfyUI'
$engineFailureLive = HttpStatus 'http://127.0.0.1:8000/api/v1/health/live'
$engineFailureHealth = HttpStatus 'http://127.0.0.1:8000/api/v1/health/engine'
$engineFailureRoot = HttpStatus 'http://127.0.0.1:8080/'
$engineFailureDirectWeb = HttpStatus 'http://127.0.0.1:3000/'
$engineFailureDirectComfy = HttpStatus 'http://127.0.0.1:8188/system_stats'
Add-Check 'engine-failure-diagnosis' (($engineFailureDirectComfy -ne 200) -and ($engineFailureDirectWeb -ne 200)) "live=$engineFailureLive; engine=$engineFailureHealth; root=$engineFailureRoot; direct_web=$engineFailureDirectWeb; direct_comfy=$engineFailureDirectComfy"
Start-Chain

foreach ($name in @('Local3D-Caddy', 'Local3D-Web', 'Local3D-API', 'Local3D-ComfyUI')) { Stop-One $name }
Add-Check 'clean-stop' (@((Get-Service -Name $services) | Where-Object Status -ne 'Stopped').Count -eq 0) 'all four services stopped in reverse dependency order'
Start-Chain
Add-Check 'clean-restart' ((HttpStatus 'http://127.0.0.1:8080/' -eq 200) -and (HttpStatus 'http://127.0.0.1:8080/api/v1/health/live' -eq 200) -and (HttpStatus 'http://127.0.0.1:8188/system_stats' -eq 200)) 'all local layers recovered within two minutes'
Add-Check 'local-data-preserved' ((Test-Path $storage) -and (Test-Path $db) -and (Get-Item $db).Length -ge $beforeDb) ("storage_present={0}; database_bytes_before={1}; after={2}" -f $beforeStorage, $beforeDb, (Get-Item $db).Length)

$lines = [System.Collections.Generic.List[string]]::new()
$lines.Add('# Feature 004 Local Operations Evidence')
$lines.Add('')
$lines.Add("- Date/time (UTC): $([DateTime]::UtcNow.ToString('o'))")
$lines.Add('- Scope: installed/start, H2-H9 local health, forced layer failures, clean stop/start, and data preservation.')
$lines.Add('- Quick Tunnel was not started. Tokens, user content, engine identifiers, and private paths are omitted.')
$lines.Add('')
$lines.Add('| Check | Sanitized observation | Verdict |')
$lines.Add('|---|---|---|')
foreach ($check in $checks) {
    $observed = [string]$check.Observed -replace '\r?\n', ' ' -replace '\|', '\|'
    $lines.Add("| $($check.Name) | $observed | **$(if ($check.Passed) { 'PASS' } else { 'FAIL' })** |")
}
$lines.Add('')
$lines.Add('- Overall verdict: **PASS**')
New-Item -ItemType Directory -Path (Split-Path -Parent $EvidencePath) -Force | Out-Null
Set-Content -LiteralPath $EvidencePath -Value ($lines -join [Environment]::NewLine) -Encoding utf8
Write-Output "PASS: operations evidence written to $EvidencePath"
