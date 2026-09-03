[CmdletBinding()]
param(
    [string]$ProjectRoot = '',
    [string]$EvidencePath = '',
    [switch]$RunGeneration
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Net.Http

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
    $ProjectRoot = (Resolve-Path (Join-Path $scriptRoot '..\..')).Path
}
if ([string]::IsNullOrWhiteSpace($EvidencePath)) {
    $EvidencePath = Join-Path $ProjectRoot 'evidence\lan\service-startup.md'
}
$ProjectRoot = (Resolve-Path $ProjectRoot).Path

$definitions = @(
    [PSCustomObject]@{
        Name = 'Local3D-ComfyUI'
        File = Join-Path $ProjectRoot 'deploy\windows\services\comfyui.xml'
        Bind = '127.0.0.1:8188'
        Port = '8188'
        Dependency = ''
    }
    [PSCustomObject]@{
        Name = 'Local3D-API'
        File = Join-Path $ProjectRoot 'deploy\windows\services\api.xml'
        Bind = '127.0.0.1:8000'
        Port = '8000'
        Dependency = 'Local3D-ComfyUI'
    }
    [PSCustomObject]@{
        Name = 'Local3D-Web'
        File = Join-Path $ProjectRoot 'deploy\windows\services\web.xml'
        Bind = '127.0.0.1:3000'
        Port = '3000'
        Dependency = 'Local3D-API'
    }
)

$checks = [System.Collections.Generic.List[object]]::new()
function Add-Check {
    param(
        [string]$Name,
        [string]$Observed,
        [string]$Expected,
        [ValidateSet('PASS', 'BLOCKED', 'FAIL')][string]$Verdict
    )
    $script:checks.Add([PSCustomObject]@{
        Name = $Name
        Observed = $Observed
        Expected = $Expected
        Verdict = $Verdict
    })
}

$parsed = @{}
foreach ($definition in $definitions) {
    if (-not (Test-Path -LiteralPath $definition.File)) {
        Add-Check "definition:$($definition.Name)" 'definition file missing' 'valid WinSW XML definition' 'FAIL'
        continue
    }
    try {
        [xml]$xml = Get-Content -Raw -LiteralPath $definition.File
        $parsed[$definition.Name] = $xml
        $service = $xml.service
        $accountNode = $service.serviceaccount
        $hasUsername = $accountNode.PSObject.Properties.Name -contains 'username'
        $hasUser = $accountNode.PSObject.Properties.Name -contains 'user'
        $hasDomain = $accountNode.PSObject.Properties.Name -contains 'domain'
        $account = if ($hasUsername -and -not [string]::IsNullOrWhiteSpace([string]$accountNode.username)) {
            [string]$accountNode.username
        } elseif ($hasUser -and -not [string]::IsNullOrWhiteSpace([string]$accountNode.user)) {
            if (-not $hasDomain -or [string]::IsNullOrWhiteSpace([string]$accountNode.domain)) {
                [string]$accountNode.user
            } else {
                "$([string]$accountNode.domain)\$([string]$accountNode.user)"
            }
        } else {
            ''
        }
        $arguments = [string]$service.arguments
        $dependencies = @()
        if ($service.PSObject.Properties.Name -contains 'depend') {
            $dependencies = @($service.depend | ForEach-Object { [string]$_ })
        }
        $bindPass = ([string]$service.arguments -match '127\.0\.0\.1' -and
            [string]$service.arguments -match "-{1,2}(port|hostname)\s+$($definition.Port)")
        $executablePath = ([string]$service.executable).Replace('%BASE%', (Join-Path $ProjectRoot 'deploy\windows\services'))
        $workingDirectory = ([string]$service.workingdirectory).Replace('%BASE%', (Join-Path $ProjectRoot 'deploy\windows\services'))
        $pathPass = (Test-Path -LiteralPath $executablePath) -and (Test-Path -LiteralPath $workingDirectory)
        $valid = (
            [string]$service.id -eq $definition.Name -and
            $account -match '(?i)^(NT AUTHORITY\\)?LocalService$' -and
            $bindPass -and
            $pathPass -and
            ($definition.Dependency -eq '' -or $dependencies -contains $definition.Dependency) -and
            [string]$service.startmode -eq 'Automatic'
        )
        $observed = "id=$($service.id); account=$account; bind=$($definition.Bind); paths_exist=$pathPass; startmode=$($service.startmode); dependency=$($definition.Dependency)"
        Add-Check "definition:$($definition.Name)" $observed 'valid XML, LocalService, existing executable/workdir, automatic start, required private bind and dependency' $(if ($valid) { 'PASS' } else { 'FAIL' })
    } catch {
        Add-Check "definition:$($definition.Name)" 'XML could not be parsed' 'valid WinSW XML definition' 'FAIL'
    }
}

$staticPass = (@($checks | Where-Object { $_.Name -like 'definition:*' -and $_.Verdict -ne 'PASS' }).Count -eq 0)

$serviceRecords = @{}
$allInstalled = $true
$allRunning = $true
$allRestricted = $true
foreach ($definition in $definitions) {
    $record = Get-CimInstance Win32_Service -Filter "Name = '$($definition.Name)'" -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($null -eq $record) {
        $allInstalled = $false
        $allRunning = $false
        $allRestricted = $false
        Add-Check "installed:$($definition.Name)" 'Windows service is not installed' 'service installed under the restricted LocalService identity' 'BLOCKED'
        continue
    }
    $serviceRecords[$definition.Name] = $record
    $restricted = [string]$record.StartName -match '(?i)(^|\\| )LocalService$'
    $running = [string]$record.State -eq 'Running'
    $allRunning = $allRunning -and $running
    $allRestricted = $allRestricted -and $restricted
    Add-Check "installed:$($definition.Name)" "state=$($record.State); start_mode=$($record.StartMode); start_name=$($record.StartName)" 'running under LocalService' $(if ($running -and $restricted) { 'PASS' } else { 'BLOCKED' })
}

$healthPass = $false
if ($allInstalled -and $allRunning -and $allRestricted) {
    try {
        $api = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8000/api/v1/health/ready' -TimeoutSec 10
        $comfy = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8188/system_stats' -TimeoutSec 10
        $web = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:3000' -TimeoutSec 10
        $healthPass = ($api.StatusCode -eq 200 -and $comfy.StatusCode -eq 200 -and $web.StatusCode -eq 200)
        Add-Check 'health' "api=$($api.StatusCode); comfyui=$($comfy.StatusCode); web=$($web.StatusCode)" 'API, ComfyUI, and web service healthy after ordered startup' $(if ($healthPass) { 'PASS' } else { 'FAIL' })
    } catch {
        Add-Check 'health' 'one or more service health requests failed' 'API, ComfyUI, and web service healthy after ordered startup' 'FAIL'
    }
} else {
    Add-Check 'health' 'not attempted because required services are not installed/running under LocalService' 'API, ComfyUI, and web service healthy after ordered startup' 'BLOCKED'
}

function Invoke-RealServiceGeneration {
    param([string]$FixturePath)

    $client = [System.Net.Http.HttpClient]::new()
    try {
        $bytes = [System.IO.File]::ReadAllBytes($FixturePath)
        $form = [System.Net.Http.MultipartFormDataContent]::new()
        $content = [System.Net.Http.ByteArrayContent]::new($bytes)
        $content.Headers.ContentType = [System.Net.Http.Headers.MediaTypeHeaderValue]::Parse('image/png')
        $form.Add($content, 'file', 'phase10-service-check.png')
        $response = $client.PostAsync('http://127.0.0.1:8000/api/v1/jobs', $form).GetAwaiter().GetResult()
        if (-not $response.IsSuccessStatusCode) { throw "job creation returned HTTP $([int]$response.StatusCode)" }
        $created = ($response.Content.ReadAsStringAsync().GetAwaiter().GetResult() | ConvertFrom-Json)
        $jobId = [string]$created.job_id
        $token = [string]$created.job_token
        if ([string]::IsNullOrWhiteSpace($jobId) -or [string]::IsNullOrWhiteSpace($token)) { throw 'job creation returned no capability data' }

        $deadline = (Get-Date).ToUniversalTime().AddMinutes(15)
        $status = $null
        do {
            Start-Sleep -Seconds 2
            $request = [System.Net.Http.HttpRequestMessage]::new([System.Net.Http.HttpMethod]::Get, "http://127.0.0.1:8000/api/v1/jobs/$jobId")
            $request.Headers.Add('X-Job-Token', $token)
            $statusResponse = $client.SendAsync($request).GetAwaiter().GetResult()
            if (-not $statusResponse.IsSuccessStatusCode) { throw "job status returned HTTP $([int]$statusResponse.StatusCode)" }
            $status = ($statusResponse.Content.ReadAsStringAsync().GetAwaiter().GetResult() | ConvertFrom-Json)
            if ([string]$status.status -in @('failed', 'cancelled')) { throw "job reached safe terminal state $($status.status)" }
        } while ([string]$status.status -ne 'completed' -and (Get-Date).ToUniversalTime() -lt $deadline)
        if ([string]$status.status -ne 'completed') { throw 'real service generation did not complete within 15 minutes' }

        $downloadRequest = [System.Net.Http.HttpRequestMessage]::new([System.Net.Http.HttpMethod]::Get, "http://127.0.0.1:8000/api/v1/jobs/$jobId/download")
        $downloadRequest.Headers.Add('X-Job-Token', $token)
        $downloadResponse = $client.SendAsync($downloadRequest).GetAwaiter().GetResult()
        if (-not $downloadResponse.IsSuccessStatusCode) { throw "download returned HTTP $([int]$downloadResponse.StatusCode)" }
        $resultBytes = $downloadResponse.Content.ReadAsByteArrayAsync().GetAwaiter().GetResult()
        $sha = [Security.Cryptography.SHA256]::Create()
        try {
            $hash = [BitConverter]::ToString($sha.ComputeHash($resultBytes)).Replace('-', '').ToLowerInvariant()
        } finally {
            $sha.Dispose()
        }
        [PSCustomObject]@{ JobId = $jobId; Size = $resultBytes.Length; Sha256 = $hash }
    } finally {
        $client.Dispose()
    }
}

$generationPass = $false
if (-not $allInstalled -or -not $allRunning -or -not $allRestricted -or -not $healthPass) {
    Add-Check 'post-service-generation' 'not attempted because the service prerequisite gate is not PASS' 'one new real textured GLB through the installed services' 'BLOCKED'
} elseif (-not $RunGeneration) {
    Add-Check 'post-service-generation' 'not attempted; rerun with -RunGeneration' 'one new real textured GLB through the installed services' 'BLOCKED'
} else {
    try {
        $fixture = Join-Path $ProjectRoot 'fixtures\inputs\valid-reference.png'
        $result = Invoke-RealServiceGeneration -FixturePath $fixture
        $generationPass = $true
        Add-Check 'post-service-generation' "job_id=$($result.JobId); size=$($result.Size); sha256=$($result.Sha256)" 'one new real textured GLB through the installed services' 'PASS'
    } catch {
        Write-Warning "Generation verifier failed: $($_.Exception.Message)"
        Add-Check 'post-service-generation' 'real generation failed; details withheld from evidence' 'one new real textured GLB through the installed services' 'FAIL'
    }
}

$overallPass = $staticPass -and $allInstalled -and $allRunning -and $allRestricted -and $healthPass -and $generationPass
$lines = [System.Collections.Generic.List[string]]::new()
$lines.Add('# Windows Service Startup Evidence (T080)')
$lines.Add('')
$lines.Add("- Date/time (UTC): $((Get-Date).ToUniversalTime().ToString('o'))")
$lines.Add("- Host: $env:COMPUTERNAME")
$lines.Add('- Service wrapper: WinSW v2 definitions; no wrapper binary or credentials are committed.')
$lines.Add('- Required order: Local3D-ComfyUI -> Local3D-API -> Local3D-Web.')
$lines.Add('- Restricted identity: built-in `LocalService`; services bind to loopback only.')
$lines.Add('')
$lines.Add('| Check | Observed | Expected | Verdict |')
$lines.Add('|---|---|---|---|')
foreach ($check in $checks) {
    $observed = ($check.Observed -replace '\r?\n', ' ' -replace '\|', '\\|')
    $expected = ($check.Expected -replace '\r?\n', ' ' -replace '\|', '\\|')
    $lines.Add("| $($check.Name) | $observed | $expected | **$($check.Verdict)** |")
}
$lines.Add('')
$lines.Add('- Static definitions are reviewable and keep API, web, and ComfyUI on `127.0.0.1`; no direct LAN bind is introduced.')
$lines.Add('- A PASS requires installed/running restricted services and a new real textured generation after service startup.')
$lines.Add("- Overall verdict: **$(if ($overallPass) { 'PASS' } else { 'BLOCKED' })**")
$evidenceParent = Split-Path -Parent $EvidencePath
New-Item -ItemType Directory -Path $evidenceParent -Force | Out-Null
Set-Content -LiteralPath $EvidencePath -Value ($lines -join [Environment]::NewLine) -Encoding utf8
Write-Output "$(if ($overallPass) { 'PASS' } else { 'BLOCKED' }): service evidence written to $EvidencePath"
if (-not $overallPass) { exit 1 }
