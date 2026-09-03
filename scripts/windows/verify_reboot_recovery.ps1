[CmdletBinding()]
param(
    [string]$ProjectRoot = '',
    [string]$EvidencePath = '',
    [switch]$ExecuteReboot,
    [switch]$AfterReboot,
    [string]$TaskName = 'Local3D-Phase10-RebootVerification'
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
    $EvidencePath = Join-Path $ProjectRoot 'evidence\lan\reboot-recovery.md'
}
$statePath = Join-Path $ProjectRoot 'storage\phase10-reboot-state.json'
$serviceNames = @('Local3D-ComfyUI', 'Local3D-API', 'Local3D-Web')

function Get-ServiceGate {
    $records = @(foreach ($name in $serviceNames) {
        Get-CimInstance Win32_Service -Filter "Name = '$name'" -ErrorAction SilentlyContinue |
            Select-Object -First 1
    })
    [PSCustomObject]@{
        Records = $records
        Installed = $records.Count -eq $serviceNames.Count
        Running = $records.Count -eq $serviceNames.Count -and
            @($records | Where-Object { [string]$_.State -ne 'Running' }).Count -eq 0
        Automatic = $records.Count -eq $serviceNames.Count -and
            @($records | Where-Object { [string]$_.StartMode -ne 'Auto' }).Count -eq 0
        Restricted = $records.Count -eq $serviceNames.Count -and
            @($records | Where-Object { [string]$_.StartName -notmatch '(?i)(^|\\| )LocalService$' }).Count -eq 0
    }
}

function Wait-ServiceStack {
    param([int]$TimeoutSeconds = 600)

    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    while ([DateTime]::UtcNow -lt $deadline) {
        $gate = Get-ServiceGate
        if ($gate.Running -and $gate.Restricted) {
            try {
                $api = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8000/api/v1/health/ready' -TimeoutSec 5
                $comfy = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8188/system_stats' -TimeoutSec 5
                $web = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:3000' -TimeoutSec 5
                if ($api.StatusCode -eq 200 -and $comfy.StatusCode -eq 200 -and $web.StatusCode -eq 200) {
                    return $gate
                }
            } catch { }
        }
        Start-Sleep -Seconds 3
    }
    throw "Service stack did not become healthy within $TimeoutSeconds seconds after boot."
}

function Write-RecoveryEvidence {
    param(
        [string]$Verdict,
        [string]$BootSummary,
        [string]$ReconciliationSummary,
        [string]$GenerationSummary,
        [string]$Action,
        [object]$Gate = (Get-ServiceGate)
    )

    $lines = [System.Collections.Generic.List[string]]::new()
    $lines.Add('# Windows Reboot Recovery Evidence (T081)')
    $lines.Add('')
    $lines.Add("- Date/time (UTC): $((Get-Date).ToUniversalTime().ToString('o'))")
    $lines.Add("- Host: $env:COMPUTERNAME")
    $lines.Add('- Scope: automatic service startup, durable-state reconciliation, and one new real generation after reboot.')
    $lines.Add('')
    $lines.Add('| Check | Observed | Expected | Verdict |')
    $lines.Add('|---|---|---|---|')
    $lines.Add("| services installed | $($Gate.Installed) | all three WinSW services installed | **$(if ($Gate.Installed) { 'PASS' } else { 'BLOCKED' })** |")
    $lines.Add("| automatic startup | $($Gate.Automatic) | all three services configured for automatic startup | **$(if ($Gate.Automatic) { 'PASS' } else { 'BLOCKED' })** |")
    $lines.Add("| restricted identity | $($Gate.Restricted) | all three services run as LocalService | **$(if ($Gate.Restricted) { 'PASS' } else { 'BLOCKED' })** |")
    $lines.Add("| machine reboot and health | $BootSummary | boot time changed and all loopback health checks passed without opening terminals | **$Verdict** |")
    $lines.Add("| non-terminal reconciliation | $ReconciliationSummary | pre-reboot processing job becomes failed/restart_recovery without duplicate submission | **$Verdict** |")
    $lines.Add("| new real generation | $GenerationSummary | one new textured GLB after automatic startup | **$Verdict** |")
    $lines.Add('')
    $lines.Add('- No raw job token is persisted in reboot state or evidence.')
    $lines.Add("- Smallest next action: $Action")
    $lines.Add("- Overall verdict: **$Verdict**")
    $parent = Split-Path -Parent $EvidencePath
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
    Set-Content -LiteralPath $EvidencePath -Value ($lines -join [Environment]::NewLine) -Encoding utf8
}

function New-ProcessingProbe {
    $fixture = Join-Path $ProjectRoot 'fixtures\inputs\valid-reference.jpg'
    $client = [System.Net.Http.HttpClient]::new()
    try {
        $bytes = [System.IO.File]::ReadAllBytes($fixture)
        $form = [System.Net.Http.MultipartFormDataContent]::new()
        $content = [System.Net.Http.ByteArrayContent]::new($bytes)
        $content.Headers.ContentType = [System.Net.Http.Headers.MediaTypeHeaderValue]::Parse('image/jpeg')
        $form.Add($content, 'file', 'phase10-reboot-probe.jpg')
        $response = $client.PostAsync('http://127.0.0.1:8000/api/v1/jobs', $form).GetAwaiter().GetResult()
        if (-not $response.IsSuccessStatusCode) { throw "reboot probe creation returned HTTP $([int]$response.StatusCode)" }
        $created = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult() | ConvertFrom-Json
        $jobId = [string]$created.job_id
        $token = [string]$created.job_token
        $deadline = [DateTime]::UtcNow.AddMinutes(2)
        do {
            $request = [System.Net.Http.HttpRequestMessage]::new([System.Net.Http.HttpMethod]::Get, "http://127.0.0.1:8000/api/v1/jobs/$jobId")
            $request.Headers.Add('X-Job-Token', $token)
            $statusResponse = $client.SendAsync($request).GetAwaiter().GetResult()
            if (-not $statusResponse.IsSuccessStatusCode) { throw "reboot probe status returned HTTP $([int]$statusResponse.StatusCode)" }
            $status = $statusResponse.Content.ReadAsStringAsync().GetAwaiter().GetResult() | ConvertFrom-Json
            if ([string]$status.status -eq 'processing') { return $jobId }
            if ([string]$status.status -in @('completed', 'failed', 'cancelled')) {
                throw "reboot probe reached terminal state $($status.status) before reboot"
            }
            Start-Sleep -Seconds 1
        } while ([DateTime]::UtcNow -lt $deadline)
        throw 'reboot probe did not enter processing within two minutes'
    } finally {
        $client.Dispose()
    }
}

$initialGate = Get-ServiceGate
if (-not $initialGate.Installed -or -not $initialGate.Automatic -or -not $initialGate.Restricted) {
    Write-RecoveryEvidence -Verdict 'BLOCKED' -BootSummary 'service installation gate is incomplete' `
        -ReconciliationSummary 'not attempted' -GenerationSummary 'not attempted' `
        -Action 'install all three Automatic LocalService services before rebooting.' -Gate $initialGate
    Write-Output "BLOCKED: reboot evidence written to $EvidencePath"
    exit 1
}

if ($AfterReboot) {
    try {
        if (-not (Test-Path -LiteralPath $statePath)) { throw 'pre-reboot state file is missing' }
        $state = Get-Content -Raw -LiteralPath $statePath | ConvertFrom-Json
        $currentBoot = (Get-CimInstance Win32_OperatingSystem).LastBootUpTime.ToUniversalTime()
        $previousBoot = [DateTime]::Parse([string]$state.boot_time_utc).ToUniversalTime()
        if ($currentBoot -le $previousBoot) { throw 'machine boot time did not change' }

        $gate = Wait-ServiceStack
        $python = Join-Path $ProjectRoot 'apps\api\.venv\Scripts\python.exe'
        $probeScript = Join-Path $ProjectRoot 'scripts\windows\check_reboot_probe.py'
        $probeJson = & $python $probeScript --database (Join-Path $ProjectRoot 'storage\jobs.sqlite3') --job-id ([string]$state.job_id)
        if ($LASTEXITCODE -ne 0) { throw 'reboot probe database check failed' }
        $probe = $probeJson | ConvertFrom-Json
        if ([string]$probe.status -ne 'failed' -or [string]$probe.error_code -ne 'restart_recovery' -or [int]$probe.attempt_count -ne 1) {
            throw 'pre-reboot processing job was not safely reconciled'
        }

        $serviceEvidence = Join-Path $ProjectRoot 'evidence\lan\service-startup.md'
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $ProjectRoot 'scripts\windows\verify_services.ps1') `
            -ProjectRoot $ProjectRoot -EvidencePath $serviceEvidence -RunGeneration
        if ($LASTEXITCODE -ne 0) { throw 'post-reboot service and generation verification did not pass' }
        $generationLine = Get-Content -LiteralPath $serviceEvidence |
            Where-Object { $_ -match '^\| post-service-generation \|' } | Select-Object -First 1
        if (-not $generationLine -or $generationLine -notmatch 'job_id=([^;]+); size=([0-9]+); sha256=([0-9a-f]{64})') {
            throw 'post-reboot generation evidence is incomplete'
        }
        $generationSummary = "job_id=$($Matches[1]); size=$($Matches[2]); sha256=$($Matches[3])"
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $statePath -Force
        Write-RecoveryEvidence -Verdict 'PASS' `
            -BootSummary "previous_boot=$($previousBoot.ToString('o')); current_boot=$($currentBoot.ToString('o')); api/comfyui/web=200" `
            -ReconciliationSummary "job_id=$($probe.job_id); status=$($probe.status); error_code=$($probe.error_code); attempt_count=$($probe.attempt_count)" `
            -GenerationSummary $generationSummary -Action 'none; retain this evidence.' -Gate $gate
        Write-Output "PASS: reboot evidence written to $EvidencePath"
        exit 0
    } catch {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
        Write-Warning "Post-reboot verifier failed: $($_.Exception.Message)"
        Write-RecoveryEvidence -Verdict 'FAIL' -BootSummary 'post-reboot verification failed' `
            -ReconciliationSummary 'not proven' -GenerationSummary 'not proven' `
            -Action 'inspect sanitized service logs and retained reboot state before retrying.'
        Write-Output "FAIL: reboot evidence written to $EvidencePath"
        exit 1
    }
}

if (-not $ExecuteReboot) {
    Write-RecoveryEvidence -Verdict 'BLOCKED' -BootSummary 'dry run; reboot not requested' `
        -ReconciliationSummary 'not attempted' -GenerationSummary 'not attempted' `
        -Action 'rerun with -ExecuteReboot from an elevated administrator session.' -Gate $initialGate
    Write-Output "BLOCKED: reboot evidence written to $EvidencePath"
    exit 1
}

$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-RecoveryEvidence -Verdict 'BLOCKED' -BootSummary 'current session is not elevated' `
        -ReconciliationSummary 'not attempted' -GenerationSummary 'not attempted' `
        -Action 'rerun from an elevated administrator session.' -Gate $initialGate
    Write-Output "BLOCKED: reboot evidence written to $EvidencePath"
    exit 1
}

$scriptPath = $MyInvocation.MyCommand.Path
$taskArguments = "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`" -ProjectRoot `"$ProjectRoot`" -EvidencePath `"$EvidencePath`" -AfterReboot -TaskName `"$TaskName`""
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $taskArguments
$trigger = New-ScheduledTaskTrigger -AtStartup
$taskPrincipal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 1)
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $taskPrincipal -Settings $settings -Force | Out-Null

try {
    $probeJobId = New-ProcessingProbe
    $state = [PSCustomObject]@{
        job_id = $probeJobId
        boot_time_utc = (Get-CimInstance Win32_OperatingSystem).LastBootUpTime.ToUniversalTime().ToString('o')
        prepared_at_utc = [DateTime]::UtcNow.ToString('o')
    }
    Set-Content -LiteralPath $statePath -Value ($state | ConvertTo-Json) -Encoding utf8
} catch {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    throw
}

Write-RecoveryEvidence -Verdict 'BLOCKED' -BootSummary 'verification task registered; reboot scheduled' `
    -ReconciliationSummary "processing probe job_id=$probeJobId prepared; result pending reboot" `
    -GenerationSummary 'pending reboot' -Action 'allow the scheduled reboot and startup verifier to finish.' -Gate $initialGate
shutdown.exe /r /t 15 /d p:4:1 /c 'Phase 10 approved reboot recovery verification'
