[CmdletBinding()]
param(
    [string]$ProjectRoot = '',
    [string]$EvidencePath = '',
    [ValidateRange(3, 3)][int]$TrialCount = 3,
    [ValidateRange(1, 3)][int]$TrialNumber = 1,
    [ValidateSet('Auto', 'Queued', 'Running')][string]$ProbeMode = 'Auto',
    [switch]$ExecuteReboot,
    [switch]$AfterReboot,
    [string]$TaskName = 'Local3D-Feature004-RebootVerification'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Net.Http
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
    $ProjectRoot = (Resolve-Path (Join-Path $scriptRoot '..\..')).Path
}
$ProjectRoot = (Resolve-Path $ProjectRoot).Path
if ([string]::IsNullOrWhiteSpace($EvidencePath)) {
    $EvidencePath = Join-Path $ProjectRoot 'evidence\feature-004\us4-restart.md'
}
$statePath = Join-Path $ProjectRoot 'storage\feature004-reboot-state.json'
$serviceNames = @('Local3D-ComfyUI', 'Local3D-API', 'Local3D-Web', 'Local3D-Caddy')

function Get-ServiceGate {
    $records = @(foreach ($name in $serviceNames) {
        Get-CimInstance Win32_Service -Filter "Name = '$name'" -ErrorAction SilentlyContinue |
            Select-Object -First 1
    })
    [PSCustomObject]@{
        Installed = $records.Count -eq 4
        Running = $records.Count -eq 4 -and @($records | Where-Object State -ne 'Running').Count -eq 0
        Automatic = $records.Count -eq 4 -and @($records | Where-Object StartMode -ne 'Auto').Count -eq 0
        Restricted = $records.Count -eq 4 -and @($records | Where-Object StartName -notmatch '(?i)LocalService$').Count -eq 0
    }
}

function Wait-ServiceStack([int]$TimeoutSeconds = 300) {
    $started = [DateTime]::UtcNow
    $deadline = $started.AddSeconds($TimeoutSeconds)
    do {
        $gate = Get-ServiceGate
        if ($gate.Running -and $gate.Restricted) {
            try {
                $checks = @(
                    'http://127.0.0.1:8080/',
                    'http://127.0.0.1:8080/api/v1/health/live',
                    'http://127.0.0.1:3000/',
                    'http://127.0.0.1:8000/api/v1/health/ready',
                    'http://127.0.0.1:8188/system_stats'
                )
                foreach ($uri in $checks) {
                    if ((Invoke-WebRequest -UseBasicParsing -Uri $uri -TimeoutSec 5).StatusCode -ne 200) {
                        throw 'not ready'
                    }
                }
                return [PSCustomObject]@{ Gate = $gate; Seconds = ([DateTime]::UtcNow - $started).TotalSeconds }
            } catch { }
        }
        Start-Sleep -Seconds 3
    } while ([DateTime]::UtcNow -lt $deadline)
    throw "Caddy and local service stack did not become healthy within $TimeoutSeconds seconds."
}

function New-AcceptedJob {
    $fixture = Join-Path $ProjectRoot 'fixtures\inputs\valid-reference.png'
    $client = [System.Net.Http.HttpClient]::new()
    try {
        $form = [System.Net.Http.MultipartFormDataContent]::new()
        $content = [System.Net.Http.ByteArrayContent]::new([System.IO.File]::ReadAllBytes($fixture))
        $content.Headers.ContentType = [System.Net.Http.Headers.MediaTypeHeaderValue]::Parse('image/png')
        $form.Add($content, 'file', 'reboot-probe.png')
        $response = $client.PostAsync('http://127.0.0.1:8000/api/v1/jobs', $form).GetAwaiter().GetResult()
        if (-not $response.IsSuccessStatusCode) { throw "probe admission returned HTTP $([int]$response.StatusCode)" }
        $created = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult() | ConvertFrom-Json
        return [string]$created.job_id
    } finally {
        $client.Dispose()
    }
}

function Read-Probes([string[]]$Ids) {
    $python = Join-Path $ProjectRoot 'apps\api\.venv\Scripts\python.exe'
    $arguments = @((Join-Path $ProjectRoot 'scripts\windows\check_reboot_probe.py'), '--database', (Join-Path $ProjectRoot 'storage\jobs.sqlite3'))
    foreach ($id in $Ids) { $arguments += @('--job-id', $id) }
    $json = & $python @arguments
    if ($LASTEXITCODE -ne 0) { throw 'sanitized reboot-probe database check failed' }
    return $json | ConvertFrom-Json
}

function Wait-DatabaseState([string]$JobId, [string]$Status, [int]$TimeoutSeconds = 120) {
    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    do {
        $record = (Read-Probes @($JobId)).jobs[0]
        if ([string]$record.status -eq $Status) { return $record }
        if ([string]$record.status -in @('completed', 'failed', 'cancelled')) {
            throw "probe reached terminal state before reboot"
        }
        Start-Sleep -Seconds 1
    } while ([DateTime]::UtcNow -lt $deadline)
    throw "probe did not reach $Status before reboot"
}

function Get-OrphanCounts {
    try {
        $queue = Invoke-RestMethod -Uri 'http://127.0.0.1:8188/queue' -TimeoutSec 5
        return "running=$(@($queue.queue_running).Count); pending=$(@($queue.queue_pending).Count); identifiers omitted"
    } catch {
        return 'engine queue unavailable; identifiers omitted'
    }
}

function Add-TrialEvidence([object]$State, [object]$ProbeResult, [double]$ReadySeconds, [string]$Verdict) {
    $lines = [System.Collections.Generic.List[string]]::new()
    if (-not (Test-Path -LiteralPath $EvidencePath)) {
        $lines.Add('# Feature 004 Notebook Restart Evidence')
        $lines.Add('')
        $lines.Add('- Three real reboot trials are required. No capability tokens, user content, engine handles, or temporary URLs are recorded.')
        $lines.Add('')
    }
    $lines.Add("## Trial $($State.trial_number) of $TrialCount - $($State.probe_mode)")
    $lines.Add('')
    $lines.Add("- Verified at (UTC): $([DateTime]::UtcNow.ToString('o'))")
    $lines.Add("- Local readiness restored in: $([math]::Round($ReadySeconds, 1)) seconds (limit: 300)")
    $lines.Add("- Boot time changed: true")
    $lines.Add("- Orphan-engine report: $(Get-OrphanCounts)")
    foreach ($job in $ProbeResult.jobs) {
        $lines.Add("- Probe `$($job.job_id)`: status=$($job.status); error=$($job.error_code); attempts=$($job.attempt_count); events=$($job.event_count)")
    }
    $lines.Add("- Verdict: **$Verdict**")
    $lines.Add('')
    New-Item -ItemType Directory -Path (Split-Path -Parent $EvidencePath) -Force | Out-Null
    Add-Content -LiteralPath $EvidencePath -Value ($lines -join [Environment]::NewLine) -Encoding utf8
}

$gate = Get-ServiceGate
if (-not $gate.Installed -or -not $gate.Automatic -or -not $gate.Restricted) {
    throw 'All four Local3D services must be installed as Automatic LocalService services.'
}

if ($AfterReboot) {
    if (-not (Test-Path -LiteralPath $statePath)) { throw 'pre-reboot state file is missing' }
    $state = Get-Content -Raw -LiteralPath $statePath | ConvertFrom-Json
    $currentBoot = (Get-CimInstance Win32_OperatingSystem).LastBootUpTime.ToUniversalTime()
    $previousBoot = [DateTime]::Parse([string]$state.boot_time_utc).ToUniversalTime()
    if ($currentBoot -le $previousBoot) { throw 'machine boot time did not change' }
    $ready = Wait-ServiceStack -TimeoutSeconds 300
    $result = Read-Probes @($state.job_ids)
    $valid = $true
    foreach ($job in $result.jobs) {
        if ([int]$job.attempt_count -gt 1) { $valid = $false }
        if ($state.probe_mode -eq 'Running' -and ([string]$job.status -ne 'failed' -or [string]$job.error_code -ne 'restart_recovery')) {
            $valid = $false
        }
    }
    $verdict = if ($valid -and $ready.Seconds -le 300) { 'PASS' } else { 'FAIL' }
    Add-TrialEvidence -State $state -ProbeResult $result -ReadySeconds $ready.Seconds -Verdict $verdict
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $statePath -Force
    if ($verdict -ne 'PASS') { exit 1 }
    Write-Output "PASS: reboot trial $($state.trial_number) recorded. Run the next trial manually; no further reboot was scheduled."
    exit 0
}

if (-not $ExecuteReboot) {
    Write-Output "READY: runner validated for trial $TrialNumber/$TrialCount. No reboot was performed; rerun with -ExecuteReboot only after explicit approval."
    exit 0
}

$principal = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'ExecuteReboot requires an elevated PowerShell session.'
}
Write-Output "START: preparing reboot trial $TrialNumber/$TrialCount; validating the local service stack."
Wait-ServiceStack -TimeoutSeconds 300 | Out-Null
Write-Output 'READY: local Caddy, Web, API, and ComfyUI checks passed.'
$selectedMode = if ($ProbeMode -eq 'Auto') { if ($TrialNumber -eq 2) { 'Queued' } else { 'Running' } } else { $ProbeMode }
$engineQueue = Invoke-RestMethod -Uri 'http://127.0.0.1:8188/queue' -TimeoutSec 5
$engineRunning = @($engineQueue.queue_running).Count
$enginePending = @($engineQueue.queue_pending).Count
if ($engineRunning -gt 0 -or $enginePending -gt 0) {
    throw "Cannot prepare reboot trial while ComfyUI is busy (running=$engineRunning; pending=$enginePending). Wait for the existing work to finish, then run this trial again."
}
Write-Output "PROBE: queue is idle; preparing a $selectedMode recovery probe."
$jobIds = [System.Collections.Generic.List[string]]::new()
if ($selectedMode -eq 'Queued') {
    $blocker = New-AcceptedJob
    Write-Output 'PROBE: waiting for the blocker job to enter processing.'
    Wait-DatabaseState -JobId $blocker -Status 'processing' | Out-Null
    $jobIds.Add((New-AcceptedJob))
    Write-Output 'PROBE: waiting for the recovery probe to enter queued state.'
    Wait-DatabaseState -JobId $jobIds[0] -Status 'queued' | Out-Null
} else {
    $jobIds.Add((New-AcceptedJob))
    Write-Output 'PROBE: waiting for the recovery probe to enter processing.'
    Wait-DatabaseState -JobId $jobIds[0] -Status 'processing' | Out-Null
}

$state = [PSCustomObject]@{
    trial_number = $TrialNumber
    probe_mode = $selectedMode
    job_ids = @($jobIds)
    boot_time_utc = (Get-CimInstance Win32_OperatingSystem).LastBootUpTime.ToUniversalTime().ToString('o')
    prepared_at_utc = [DateTime]::UtcNow.ToString('o')
}
Set-Content -LiteralPath $statePath -Value ($state | ConvertTo-Json) -Encoding utf8
$scriptPath = $MyInvocation.MyCommand.Path
$arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`" -ProjectRoot `"$ProjectRoot`" -EvidencePath `"$EvidencePath`" -TrialCount $TrialCount -TrialNumber $TrialNumber -AfterReboot -TaskName `"$TaskName`""
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $arguments
$trigger = New-ScheduledTaskTrigger -AtStartup
$taskPrincipal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 15)
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $taskPrincipal -Settings $settings -Force | Out-Null

Write-Output "REBOOT PENDING: trial $TrialNumber/$TrialCount ($selectedMode) begins in 15 seconds."
shutdown.exe /r /t 15 /d p:4:1 /c 'Feature 004 approved reboot recovery verification'
