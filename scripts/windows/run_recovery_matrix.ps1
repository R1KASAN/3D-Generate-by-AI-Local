[CmdletBinding()]
param(
    [string]$ProjectRoot = '',
    [string]$EvidencePath = '',
    [switch]$ExecuteServiceRestarts,
    [int]$HealthTimeoutSeconds = 300
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
    $ProjectRoot = (Resolve-Path (Join-Path $scriptRoot '..\..')).Path
}
if ([string]::IsNullOrWhiteSpace($EvidencePath)) {
    $EvidencePath = Join-Path $ProjectRoot 'evidence\feature-004\us4-recovery-matrix.md'
}
Set-Location -LiteralPath $ProjectRoot

$serviceNames = @('Local3D-ComfyUI', 'Local3D-API', 'Local3D-Web', 'Local3D-Caddy')
$checks = [System.Collections.Generic.List[object]]::new()

function Add-Check([string]$Name, [bool]$Passed, [string]$Observed) {
    $script:checks.Add([PSCustomObject]@{ Name = $Name; Passed = $Passed; Observed = $Observed })
    if (-not $Passed) { throw "$Name failed: $Observed" }
}

function Wait-Http([string]$Uri, [int]$TimeoutSeconds) {
    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    do {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $Uri -TimeoutSec 5
            if ($response.StatusCode -eq 200) { return }
        } catch { }
        Start-Sleep -Seconds 2
    } while ([DateTime]::UtcNow -lt $deadline)
    throw "health check did not recover within $TimeoutSeconds seconds"
}

function Get-OrphanSummary {
    try {
        $queue = Invoke-RestMethod -Uri 'http://127.0.0.1:8188/queue' -TimeoutSec 5
        [PSCustomObject]@{
            Running = @($queue.queue_running).Count
            Pending = @($queue.queue_pending).Count
            Reachable = $true
        }
    } catch {
        [PSCustomObject]@{ Running = -1; Pending = -1; Reachable = $false }
    }
}

function Invoke-PytestCase([string]$Name, [string[]]$Targets) {
    $output = (& uv run --project apps/api pytest @Targets -q 2>&1 | Out-String).Trim()
    Add-Check $Name ($LASTEXITCODE -eq 0) ($output -replace '\r?\n', ' ')
}

$gate = @(Get-Service -Name $serviceNames -ErrorAction SilentlyContinue)
Add-Check 'service definitions' ($gate.Count -eq 4) 'four approved single-node services installed'
$before = Get-OrphanSummary
Add-Check 'orphan-engine baseline' $before.Reachable (
    "queue_running={0}; queue_pending={1}; identifiers omitted" -f $before.Running, $before.Pending
)

Invoke-PytestCase 'invalid input and pressure' @(
    'apps/api/tests/contract/test_job_status_and_failures.py',
    'apps/api/tests/integration/test_submission_bounds.py'
)
Invoke-PytestCase 'low disk and orphan cleanup' @(
    'apps/api/tests/integration/test_orphan_cleanup.py'
)
Invoke-PytestCase 'hang timeout cancellation missing output' @(
    'apps/api/tests/integration/test_adapter_recovery.py',
    'apps/api/tests/integration/test_status_poll_retry_state.py'
)
Invoke-PytestCase 'corrupt and partial output rejection' @(
    'apps/api/tests/unit/test_glb_publication.py',
    'apps/api/tests/unit/test_comfy_output_discovery.py'
)

if ($ExecuteServiceRestarts) {
    $principal = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw 'ExecuteServiceRestarts requires an elevated PowerShell session.'
    }
    if ($before.Running -ne 0 -or $before.Pending -ne 0) {
        throw 'ComfyUI queue is not empty; refusing a controlled service restart.'
    }
    $targets = @(
        @{ Name = 'Local3D-Caddy'; Uri = 'http://127.0.0.1:8080/' },
        @{ Name = 'Local3D-Web'; Uri = 'http://127.0.0.1:3000/' },
        @{ Name = 'Local3D-API'; Uri = 'http://127.0.0.1:8000/api/v1/health/live' },
        @{ Name = 'Local3D-ComfyUI'; Uri = 'http://127.0.0.1:8188/system_stats' }
    )
    foreach ($target in $targets) {
        $started = [DateTime]::UtcNow
        Restart-Service -Name $target.Name -Force
        # Windows dependency handling can stop downstream services when API or
        # ComfyUI restarts. Restore the approved chain in dependency order.
        foreach ($serviceName in $serviceNames) {
            if ((Get-Service -Name $serviceName).Status -ne 'Running') {
                Start-Service -Name $serviceName
            }
        }
        Wait-Http -Uri $target.Uri -TimeoutSeconds $HealthTimeoutSeconds
        Wait-Http -Uri 'http://127.0.0.1:8080/api/v1/health/live' -TimeoutSeconds $HealthTimeoutSeconds
        $elapsed = ([DateTime]::UtcNow - $started).TotalSeconds
        Add-Check "$($target.Name) controlled restart" $true ("healthy after {0:n1}s" -f $elapsed)
    }
}

$after = Get-OrphanSummary
Add-Check 'orphan-engine result' ($after.Reachable -and $after.Running -eq 0 -and $after.Pending -eq 0) (
    "queue_running={0}; queue_pending={1}; identifiers omitted" -f $after.Running, $after.Pending
)

$lines = [System.Collections.Generic.List[string]]::new()
$lines.Add('# Feature 004 Application Recovery Matrix')
$lines.Add('')
$lines.Add("- Date/time (UTC): $([DateTime]::UtcNow.ToString('o'))")
$lines.Add('- Scope: queued/running reconciliation, orphan-engine reporting, and optional controlled service restarts.')
$lines.Add('- Engine prompt identifiers, tokens, user content, and private paths are omitted.')
$lines.Add('')
$lines.Add('| Check | Sanitized observation | Verdict |')
$lines.Add('|---|---|---|')
foreach ($check in $checks) {
    $observed = [string]$check.Observed -replace '\r?\n', ' ' -replace '\|', '\|'
    $verdict = if ($check.Passed) { 'PASS' } else { 'FAIL' }
    $lines.Add("| $($check.Name) | $observed | **$verdict** |")
}
$lines.Add('')
$lines.Add("- Controlled service restarts executed: **$([bool]$ExecuteServiceRestarts)**")
$lines.Add('- Overall verdict: **PASS**')
New-Item -ItemType Directory -Path (Split-Path -Parent $EvidencePath) -Force | Out-Null
Set-Content -LiteralPath $EvidencePath -Value ($lines -join [Environment]::NewLine) -Encoding utf8
Write-Output "PASS: recovery matrix written to $EvidencePath"
