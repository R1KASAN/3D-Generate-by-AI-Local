[CmdletBinding()]
param(
    [string]$CloudflaredPath = 'cloudflared',
    [ValidateRange(1, 65535)][int]$CaddyPort = 8080,
    [string]$StatePath = (Join-Path $env:ProgramData 'Local3D\quick-tunnel.json')
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Assert-NoConflictingDefaultConfig {
    $configRoot = Join-Path $env:USERPROFILE '.cloudflared'
    foreach ($name in @('config.yaml', 'config.yml')) {
        $path = Join-Path $configRoot $name
        if (-not (Test-Path -LiteralPath $path)) { continue }
        $body = Get-Content -Raw -LiteralPath $path
        if ($body -match '(?im)^\s*(tunnel|credentials-file|ingress)\s*:') {
            throw "Refusing Quick Tunnel because the default cloudflared config contains a named-tunnel setting: $name"
        }
    }
}

Assert-NoConflictingDefaultConfig

try {
    Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:${CaddyPort}/" -TimeoutSec 5 | Out-Null
    Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:${CaddyPort}/api/v1/health/live" -TimeoutSec 5 | Out-Null
} catch {
    throw "Caddy and the local API must be healthy on 127.0.0.1:${CaddyPort} before starting the Quick Tunnel."
}

Write-Output 'Starting temporary non-production Cloudflare Quick Tunnel; URL is public and not authentication.'
# Runtime command: cloudflared tunnel --url http://127.0.0.1:8080 --loglevel info
Write-Output 'The command will print a temporary https://<random>.trycloudflare.com address.'
Write-Output 'Each launch creates a new URL. An older URL can return Cloudflare Error 1033 and must not be reused.'
Write-Output 'No URL or token is written to the repository. Stop with Ctrl+C.'
$stateDirectory = Split-Path -Parent $StatePath
New-Item -ItemType Directory -Path $stateDirectory -Force | Out-Null
$stdoutPath = Join-Path $stateDirectory 'quick-tunnel.stdout.log'
$stderrPath = Join-Path $stateDirectory 'quick-tunnel.stderr.log'

if (Test-Path -LiteralPath $StatePath) {
    try {
        $existingState = Get-Content -LiteralPath $StatePath -Raw | ConvertFrom-Json
        $existingProcess = Get-Process -Id ([int]$existingState.pid) -ErrorAction SilentlyContinue
        if ($null -ne $existingProcess -and $existingProcess.ProcessName -eq 'cloudflared') {
            throw "A Quick Tunnel is already running with PID $($existingProcess.Id). Stop it before starting another session."
        }
    } catch {
        if ($_.Exception.Message -like 'A Quick Tunnel is already running*') { throw }
    }
    Remove-Item -LiteralPath $StatePath -Force -ErrorAction SilentlyContinue
}

# These are operator-owned transient logs outside the repository. Clear them
# before every launch so an expired URL from an earlier session cannot be
# mistaken for the current URL and produce Cloudflare Error 1033.
Remove-Item -LiteralPath $stdoutPath, $stderrPath -Force -ErrorAction SilentlyContinue
$process = Start-Process -FilePath $CloudflaredPath -ArgumentList @('tunnel', '--url', "http://127.0.0.1:${CaddyPort}", '--loglevel', 'info') -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath -PassThru -WindowStyle Hidden
$stateJson = @{ pid = $process.Id; started_at = [DateTime]::UtcNow.ToString('o'); origin = "http://127.0.0.1:${CaddyPort}" } | ConvertTo-Json
[System.IO.File]::WriteAllText($StatePath, $stateJson)
$stdoutLinesShown = 0
$stderrLinesShown = 0
$temporaryUrlShown = $false

function Write-NewTunnelLogLines {
    param(
        [Parameter(Mandatory = $true)][string]$LiteralPath,
        [Parameter(Mandatory = $true)][ref]$LinesShown
    )

    if (-not (Test-Path -LiteralPath $LiteralPath)) { return }
    $lines = @(Get-Content -LiteralPath $LiteralPath)
    if ($lines.Count -le $LinesShown.Value) { return }
    foreach ($line in ($lines | Select-Object -Skip $LinesShown.Value)) {
        Write-Output $line
        if (-not $script:temporaryUrlShown -and $line -match 'https://[a-z0-9-]+\.trycloudflare\.com') {
            Write-Output "TEMPORARY NON-PRODUCTION URL: $($Matches[0])"
            Write-Output 'Use only this URL for the current session; previous Quick Tunnel URLs are expired.'
            $script:temporaryUrlShown = $true
        }
    }
    $LinesShown.Value = $lines.Count
}

try {
    while (-not $process.HasExited) {
        Write-NewTunnelLogLines -LiteralPath $stdoutPath -LinesShown ([ref]$stdoutLinesShown)
        Write-NewTunnelLogLines -LiteralPath $stderrPath -LinesShown ([ref]$stderrLinesShown)
        Start-Sleep -Seconds 2
        $process.Refresh()
    }
    Write-NewTunnelLogLines -LiteralPath $stdoutPath -LinesShown ([ref]$stdoutLinesShown)
    Write-NewTunnelLogLines -LiteralPath $stderrPath -LinesShown ([ref]$stderrLinesShown)
    exit $process.ExitCode
} finally {
    if (-not $process.HasExited) {
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
    }
    Remove-Item -LiteralPath $StatePath -Force -ErrorAction SilentlyContinue
}
