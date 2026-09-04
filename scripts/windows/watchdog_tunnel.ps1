[CmdletBinding()]
param(
    [string]$TunnelAddress = '10.10.0.2',
    [string]$EdgeTunnelAddress = '10.10.0.1',
    [ValidateRange(1, 65535)][int]$WebPort = 3000,
    [string]$WireGuardServiceName = 'WireGuardTunnel$upstream',
    [string]$WebServiceName = 'Local3D-Web',
    [string]$StateFile = (Join-Path $env:ProgramData 'Local3D\watchdog-state.json'),
    [int]$CooldownMinutes = 15,
    [int]$MaxRestartsBeforeAlert = 3
)

# Recovery watchdog for the laptop-side tunnel + web service, run every 5
# minutes as a Scheduled Task.
#
# This deliberately diagnoses BEFORE it acts. WireGuard failing and Next.js
# failing are different problems at different layers, and restarting the
# wrong layer does not fix anything - restarting Local3D-Web while the
# tunnel itself is down just produces a service that dies again on bind,
# repeatedly, without ever addressing the real fault. See the plan's
# decision tree:
#
#   WG handshake stale        -> restart the WireGuard tunnel service only
#   WG healthy, web not up    -> restart Local3D-Web only
#   both healthy              -> do nothing
#
# A cooldown and an escalating-failure cutoff prevent an unbounded restart
# loop: if the same layer needed a restart more than $MaxRestartsBeforeAlert
# times in a row, stop touching it and write an error-level log entry
# instead. At that point the problem is very likely external (e.g. the
# network the laptop is on blocks outbound UDP) and keeps restarting will
# not fix it - it will only flood the log and hide the real cause.

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-State {
    if (Test-Path -LiteralPath $StateFile) {
        try { return Get-Content -LiteralPath $StateFile -Raw | ConvertFrom-Json } catch {}
    }
    return [pscustomobject]@{
        WireGuardRestartCount = 0
        WireGuardLastRestart  = $null
        WebRestartCount       = 0
        WebLastRestart        = $null
    }
}

function Save-State($state) {
    $dir = Split-Path -Parent $StateFile
    if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    $state | ConvertTo-Json | Set-Content -LiteralPath $StateFile -Encoding UTF8
}

function Test-CooldownElapsed($lastRestart) {
    if ($null -eq $lastRestart -or $lastRestart -eq '') { return $true }
    return ([DateTime]::UtcNow - [DateTime]::Parse($lastRestart)) -gt (New-TimeSpan -Minutes $CooldownMinutes)
}

function Write-Log($level, $message) {
    $line = "[{0:o}] [{1}] {2}" -f [DateTime]::UtcNow, $level, $message
    Write-Output $line
    $logDir = Join-Path $env:ProgramData 'Local3D'
    if (-not (Test-Path -LiteralPath $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
    Add-Content -LiteralPath (Join-Path $logDir 'watchdog.log') -Value $line
}

$state = Get-State

# --- Layer 1: is the tunnel itself healthy? ---
$tunnelHealthy = $false
try {
    $tunnelHealthy = [bool](Test-Connection -TargetName $EdgeTunnelAddress -Count 1 -Quiet -ErrorAction SilentlyContinue)
} catch {
    $tunnelHealthy = $false
}

if (-not $tunnelHealthy) {
    if ($state.WireGuardRestartCount -ge $MaxRestartsBeforeAlert) {
        Write-Log 'ERROR' "WireGuard tunnel unreachable and restart limit ($MaxRestartsBeforeAlert) already reached without recovery. NOT restarting again - this is very likely an external condition (e.g. the current network blocks outbound UDP/51820) that a restart cannot fix. Manual investigation required; see docs/operations/tunnel-setup.md."
        exit 1
    }
    if (-not (Test-CooldownElapsed $state.WireGuardLastRestart)) {
        Write-Log 'WARN' "WireGuard tunnel unreachable but within the $CooldownMinutes-minute cooldown of its last restart. Waiting."
        exit 0
    }
    Write-Log 'WARN' "WireGuard tunnel unreachable (no reply from $EdgeTunnelAddress). Restarting the tunnel service, NOT the web service - the fault is at the tunnel layer."
    try {
        Restart-Service -Name $WireGuardServiceName -Force -ErrorAction Stop
        $state.WireGuardRestartCount = [int]$state.WireGuardRestartCount + 1
        $state.WireGuardLastRestart = [DateTime]::UtcNow.ToString('o')
        Save-State $state
        Write-Log 'INFO' "Restarted $WireGuardServiceName (attempt $($state.WireGuardRestartCount) of $MaxRestartsBeforeAlert)."
    } catch {
        Write-Log 'ERROR' "Failed to restart ${WireGuardServiceName}: $($_.Exception.Message)"
    }
    exit 0
}

# Tunnel is healthy - reset its failure counter now that it has recovered.
if ([int]$state.WireGuardRestartCount -ne 0) {
    $state.WireGuardRestartCount = 0
    $state.WireGuardLastRestart = $null
    Save-State $state
}

# --- Layer 2: tunnel is fine, is the web service actually listening? ---
$webListening = [bool](Get-NetTCPConnection -State Listen -LocalAddress $TunnelAddress -LocalPort $WebPort -ErrorAction SilentlyContinue)

if (-not $webListening) {
    if ($state.WebRestartCount -ge $MaxRestartsBeforeAlert) {
        Write-Log 'ERROR' "Local3D-Web is not listening on ${TunnelAddress}:${WebPort} and restart limit ($MaxRestartsBeforeAlert) already reached. NOT restarting again - investigate manually (check the service's own logs, not just this watchdog's)."
        exit 1
    }
    if (-not (Test-CooldownElapsed $state.WebLastRestart)) {
        Write-Log 'WARN' "Local3D-Web not listening but within the $CooldownMinutes-minute cooldown of its last restart. Waiting."
        exit 0
    }
    Write-Log 'WARN' "Tunnel is healthy but Local3D-Web is not listening on ${TunnelAddress}:${WebPort}. Restarting the web service - the fault is at the app layer, not the tunnel."
    try {
        Restart-Service -Name $WebServiceName -Force -ErrorAction Stop
        $state.WebRestartCount = [int]$state.WebRestartCount + 1
        $state.WebLastRestart = [DateTime]::UtcNow.ToString('o')
        Save-State $state
        Write-Log 'INFO' "Restarted $WebServiceName (attempt $($state.WebRestartCount) of $MaxRestartsBeforeAlert)."
    } catch {
        Write-Log 'ERROR' "Failed to restart ${WebServiceName}: $($_.Exception.Message)"
    }
    exit 0
}

# Both healthy - reset the web failure counter and do nothing.
if ([int]$state.WebRestartCount -ne 0) {
    $state.WebRestartCount = 0
    $state.WebLastRestart = $null
    Save-State $state
}

Write-Log 'INFO' 'Tunnel and web service both healthy. No action taken.'
exit 0
