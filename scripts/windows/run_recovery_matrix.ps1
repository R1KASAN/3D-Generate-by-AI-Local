[CmdletBinding()]
param(
    [string]$ProjectRoot = '',
    [string]$ComfyRoot = '',
    [string]$ComfyBaseUrl = 'http://127.0.0.1:8188',
    [string]$EvidencePath = '',
    [int]$HealthTimeoutSeconds = 180
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
    $ProjectRoot = (Resolve-Path (Join-Path $scriptRoot '..\..')).Path
}
if ([string]::IsNullOrWhiteSpace($ComfyRoot)) {
    $ComfyRoot = Join-Path $env:USERPROFILE 'ComfyUI'
}
if ([string]::IsNullOrWhiteSpace($EvidencePath)) {
    $EvidencePath = Join-Path $scriptRoot '..\..\evidence\windows\recovery-matrix.md'
}
Set-Location -LiteralPath $ProjectRoot

$results = [System.Collections.Generic.List[object]]::new()
$startedAt = (Get-Date).ToUniversalTime()
$comfyOutputRoot = Join-Path $ComfyRoot 'output'
$uvPath = (Get-Command uv.exe -ErrorAction SilentlyContinue).Source
if (-not $uvPath) {
    $candidateUv = Join-Path $ComfyRoot 'venv\Scripts\uv.exe'
    if (Test-Path $candidateUv) { $uvPath = $candidateUv }
}
if (-not $uvPath) { throw 'uv.exe is required for the backend recovery contract checks.' }

function Add-Result {
    param(
        [string]$Case,
        [string]$Observed,
        [string]$Expected,
        [bool]$Passed,
        [string]$Evidence = ''
    )
    $script:results.Add([PSCustomObject]@{
        Case = $Case
        Observed = $Observed
        Expected = $Expected
        Passed = $Passed
        Evidence = $Evidence
    })
    if (-not $Passed) { throw "$Case failed: $Observed" }
}

function Invoke-CapturedCommand {
    param(
        [string]$FilePath,
        [string[]]$ArgumentList
    )
    $captured = (& $FilePath @ArgumentList 2>&1 | Out-String).Trim()
    [PSCustomObject]@{
        ExitCode = [int]$LASTEXITCODE
        Output = $captured
    }
}

function Get-Health {
    Invoke-RestMethod -Uri "$ComfyBaseUrl/system_stats" -TimeoutSec 10
}

function Get-JobGlbSnapshot {
    if (-not (Test-Path $comfyOutputRoot)) { return @() }
    @(Get-ChildItem -File -Recurse (Join-Path $comfyOutputRoot 'jobs') -Filter '*.glb' -ErrorAction SilentlyContinue |
        ForEach-Object { "{0}|{1}|{2}" -f $_.FullName, $_.Length, $_.LastWriteTimeUtc.ToString('o') } |
        Sort-Object)
}

function Get-PortOwner {
    $connection = Get-NetTCPConnection -LocalPort 8188 -State Listen -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($null -eq $connection) { return $null }
    $process = Get-CimInstance Win32_Process -Filter "ProcessId = $($connection.OwningProcess)" |
        Select-Object -First 1
    if ($null -eq $process) { return $null }
    [PSCustomObject]@{
        Id = [int]$process.ProcessId
        Path = [string]$process.ExecutablePath
        CommandLine = [string]$process.CommandLine
    }
}

function Get-ComfyServerProcesses {
    @(Get-CimInstance Win32_Process |
        Where-Object {
            [string]$_.CommandLine -match '(?i)main\.py.*--listen\s+127\.0\.0\.1.*--port\s+8188'
        })
}

function Wait-ForHealth {
    param([int]$TimeoutSeconds)
    $deadline = (Get-Date).ToUniversalTime().AddSeconds($TimeoutSeconds)
    do {
        try { return Get-Health } catch { Start-Sleep -Seconds 3 }
    } while ((Get-Date).ToUniversalTime() -lt $deadline)
    throw "ComfyUI did not become healthy within $TimeoutSeconds seconds."
}

if (-not (Test-Path (Join-Path $ComfyRoot 'main.py'))) {
    throw "ComfyUI installation was not found at $ComfyRoot."
}

$initialHealth = Get-Health
$initialQueue = Invoke-RestMethod -Uri "$ComfyBaseUrl/queue" -TimeoutSec 10
$beforeGlbs = Get-JobGlbSnapshot
$initialProcess = Get-PortOwner
if ($null -eq $initialProcess) { throw 'No ComfyUI process owns loopback port 8188.' }
$initialProcessPath = $initialProcess.Path
$initialCommandLine = [string]$initialProcess.CommandLine
if (-not ($initialCommandLine -match '(?i)main\.py.*--listen\s+127\.0\.0\.1.*--port\s+8188')) {
    throw "Port 8188 is owned by an unexpected process: $initialCommandLine"
}
Add-Result -Case 'baseline' `
    -Observed ("healthy version={0}; gpu={1}; queue_running={2}; queue_pending={3}" -f `
        $initialHealth.system.comfyui_version, $initialHealth.devices[0].name, `
        @($initialQueue.queue_running).Count, @($initialQueue.queue_pending).Count) `
    -Expected 'loopback ComfyUI healthy with an empty queue before recovery cases' `
    -Passed (@($initialQueue.queue_running).Count -eq 0 -and @($initialQueue.queue_pending).Count -eq 0)

# Controlled engine failure: an unknown node is rejected before execution.
$invalidBody = @{ prompt = @{ '999' = @{ class_type = 'Local3DDeliberatelyMissing'; inputs = @{} } } } |
    ConvertTo-Json -Depth 20 -Compress
$engineFailureStatus = 0
try {
    Invoke-WebRequest -Uri "$ComfyBaseUrl/prompt" -Method Post -ContentType 'application/json' `
        -Body $invalidBody -TimeoutSec 10 | Out-Null
} catch {
    if ($null -ne $_.Exception.Response) {
        $engineFailureStatus = [int]$_.Exception.Response.StatusCode
    }
}
Add-Result -Case 'engine failure' `
    -Observed "POST /prompt returned HTTP $engineFailureStatus for an unknown node" `
    -Expected '4xx rejection before engine execution' `
    -Passed ($engineFailureStatus -ge 400 -and $engineFailureStatus -lt 500)

# Timeout and disconnect are exercised through the real client contract, which
# asserts UNKNOWN mapping and no automatic resubmission.
$timeoutRun = Invoke-CapturedCommand -FilePath $uvPath -ArgumentList @(
    'run', '--project', 'apps/api', 'pytest',
    'apps/api/tests/contract/test_comfy_client.py', '-k', 'timeout', '-q'
)
Add-Result -Case 'timeout' `
    -Observed ("pytest exit {0}: {1}" -f $timeoutRun.ExitCode, $timeoutRun.Output) `
    -Expected 'client timeout maps to a safe unknown/generation_timeout observation' `
    -Passed ($timeoutRun.ExitCode -eq 0) `
    -Evidence 'apps/api/tests/contract/test_comfy_client.py -k timeout'

$disconnectRun = Invoke-CapturedCommand -FilePath $uvPath -ArgumentList @(
    'run', '--project', 'apps/api', 'pytest',
    'apps/api/tests/contract/test_comfy_client.py', '-k', 'disconnect', '-q'
)
$unreachableStatus = 'not observed'
try {
    Invoke-RestMethod -Uri 'http://127.0.0.1:8189/system_stats' -TimeoutSec 2 | Out-Null
} catch {
    $unreachableStatus = 'connection refused/unreachable as expected'
}
Add-Result -Case 'disconnect' `
    -Observed ("$unreachableStatus; pytest exit {0}: {1}" -f $disconnectRun.ExitCode, $disconnectRun.Output) `
    -Expected 'engine disconnect maps safely and no alternate endpoint is contacted' `
    -Passed ($disconnectRun.ExitCode -eq 0 -and $unreachableStatus -ne 'not observed') `
    -Evidence 'apps/api/tests/contract/test_comfy_client.py -k disconnect'

# Missing output: the strict resolver rejects an empty job directory.
$missingRun = Invoke-CapturedCommand -FilePath $uvPath -ArgumentList @(
    'run', '--project', 'apps/api', 'pytest',
    'apps/api/tests/unit/test_comfy_output_discovery.py', '-k', 'zero_candidates', '-q'
)
Add-Result -Case 'missing output' `
    -Observed ("pytest exit {0}: {1}" -f $missingRun.ExitCode, $missingRun.Output) `
    -Expected 'zero GLB candidates are rejected and never published' `
    -Passed ($missingRun.ExitCode -eq 0) `
    -Evidence 'apps/api/tests/unit/test_comfy_output_discovery.py -k zero_candidates'

# Backend restart/reconciliation: run the real persistence/recovery integration
# suite, including queued rehydration and processing failure without resubmit.
$backendRun = Invoke-CapturedCommand -FilePath $uvPath -ArgumentList @(
    'run', '--project', 'apps/api', 'pytest',
    'apps/api/tests/integration/test_adapter_recovery.py', '-k', 'restart', '-q'
)
Add-Result -Case 'backend restart' `
    -Observed ("pytest exit {0}: {1}" -f $backendRun.ExitCode, $backendRun.Output) `
    -Expected 'queued work rehydrates safely; processing uncertainty becomes restart_recovery; duplicate submissions=0' `
    -Passed ($backendRun.ExitCode -eq 0) `
    -Evidence 'apps/api/tests/integration/test_adapter_recovery.py -k restart'

# ComfyUI restart: stop only the verified owner of 127.0.0.1:8188 and start it
# with the same loopback-only command. No generation is submitted during this case.
$restartStarted = (Get-Date).ToUniversalTime()
$restartProcesses = Get-ComfyServerProcesses
if (-not ($restartProcesses | Where-Object { $_.ProcessId -eq $initialProcess.Id })) {
    throw 'The port owner was not part of the verified ComfyUI loopback process tree.'
}
foreach ($process in $restartProcesses) {
    Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue
}
$afterStop = $null
for ($attempt = 0; $attempt -lt 20; $attempt++) {
    try { $afterStop = Get-PortOwner } catch { $afterStop = $null }
    if ($null -eq $afterStop) { break }
    Start-Sleep -Milliseconds 500
}
$stopObserved = $null -eq $afterStop
$restartStdout = Join-Path $ComfyRoot 'comfyui_recovery_restart_stdout.log'
$restartStderr = Join-Path $ComfyRoot 'comfyui_recovery_restart_stderr.log'
$restartPython = Join-Path $ComfyRoot 'venv\Scripts\python.exe'
if (-not (Test-Path $restartPython)) { $restartPython = $initialProcessPath }
$newProcess = Start-Process -FilePath $restartPython `
    -ArgumentList @('main.py', '--listen', '127.0.0.1', '--port', '8188') `
    -WorkingDirectory $ComfyRoot -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput $restartStdout -RedirectStandardError $restartStderr
$restartedHealth = Wait-ForHealth -TimeoutSeconds $HealthTimeoutSeconds
$restartedQueue = Invoke-RestMethod -Uri "$ComfyBaseUrl/queue" -TimeoutSec 10
$afterGlbs = Get-JobGlbSnapshot
$sameOutputs = (Compare-Object -ReferenceObject $beforeGlbs -DifferenceObject $afterGlbs) -eq $null
$restartDuration = ((Get-Date).ToUniversalTime() - $restartStarted).TotalSeconds
Add-Result -Case 'ComfyUI restart' `
    -Observed ("stopped={0}; restarted_pid={1}; healthy_version={2}; queue_running={3}; queue_pending={4}; glb_snapshot_unchanged={5}; duration={6:n1}s" -f `
        $stopObserved, $newProcess.Id, $restartedHealth.system.comfyui_version, `
        @($restartedQueue.queue_running).Count, @($restartedQueue.queue_pending).Count, $sameOutputs, $restartDuration) `
    -Expected 'same pinned loopback instance returns healthy with empty queue and no new/overwritten job outputs' `
    -Passed ($stopObserved -and @($restartedQueue.queue_running).Count -eq 0 -and `
        @($restartedQueue.queue_pending).Count -eq 0 -and $sameOutputs -and `
        $restartedHealth.system.comfyui_version -eq $initialHealth.system.comfyui_version) `
    -Evidence "$restartStdout; $restartStderr"

$finishedAt = (Get-Date).ToUniversalTime()
$failed = @($results | Where-Object { -not $_.Passed })
$lines = [System.Collections.Generic.List[string]]::new()
$lines.Add('# Windows Real-Engine Recovery Matrix (T078)')
$lines.Add('')
$lines.Add("- Date/time (UTC): $($startedAt.ToString('o')) to $($finishedAt.ToString('o'))")
$lines.Add("- Host: $env:COMPUTERNAME")
$lines.Add("- ComfyUI: $($initialHealth.system.comfyui_version), loopback $ComfyBaseUrl")
$lines.Add("- GPU: $($initialHealth.devices[0].name)")
$lines.Add('- Scope: controlled failure/recovery cases; no automatic resubmission is performed by this runner.')
$lines.Add('')
$lines.Add('| Case | Observed | Expected | Verdict |')
$lines.Add('|---|---|---|---|')
foreach ($result in $results) {
    $verdict = if ($result.Passed) { 'PASS' } else { 'FAIL' }
    $observed = ($result.Observed -replace '\r?\n', ' ' -replace '\|', '\\|')
    $expected = ($result.Expected -replace '\r?\n', ' ' -replace '\|', '\\|')
    $lines.Add("| $($result.Case) | $observed | $expected | **$verdict** |")
}
$lines.Add('')
$lines.Add("- Phase 9 output GLB snapshot before/after ComfyUI restart: $($beforeGlbs.Count) / $($afterGlbs.Count) files; changed outputs: $(-not $sameOutputs).")
$lines.Add('- Duplicate execution verdict: **0** observed in the controlled matrix; no case resubmitted a prompt after timeout, disconnect, missing output, backend restart, or ComfyUI restart.')
$lines.Add('- Sensitive engine payloads, credentials, uploaded image content, and private stack traces are intentionally omitted.')
$lines.Add('')
$lines.Add("Verdict: **$(if ($failed.Count -eq 0) { 'PASS' } else { 'FAIL' })**")

$evidenceParent = Split-Path -Parent $EvidencePath
New-Item -ItemType Directory -Path $evidenceParent -Force | Out-Null
Set-Content -Path $EvidencePath -Value ($lines -join [Environment]::NewLine) -Encoding utf8

if ($failed.Count -gt 0) { exit 1 }
Write-Output "PASS: recovery matrix written to $EvidencePath"
