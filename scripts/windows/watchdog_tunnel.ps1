[CmdletBinding()]
param(
    [string]$EdgeTunnelAddress = '10.10.0.1',
    [string]$WireGuardInterface = 'upstream',
    [string]$WebListenAddress = '127.0.0.1',
    [ValidateRange(1, 65535)][int]$WebPort = 3000,
    [string]$ComfyBaseUrl = 'http://127.0.0.1:8188',
    [string]$WireGuardServiceName = 'WireGuardTunnel$upstream',
    [string]$WebServiceName = 'Local3D-Web',
    [string]$ComfyServiceName = 'Local3D-ComfyUI',
    [string]$StateFile = (Join-Path $env:ProgramData 'Local3D\watchdog-state.json'),
    [int]$CooldownMinutes = 15,
    [ValidateRange(1, 3)][int]$MaxRestartsBeforeAlert = 3,
    [int]$DependentGraceMinutes = 5
)

# Recovery watchdog for all four laptop-owned health-chain layers
# (contracts/health-chain.md H1/H4), run every 5 minutes as a Scheduled
# Task: PrivateBinding -> JobService -> Gpu -> AiEngine.
#
# This deliberately diagnoses BEFORE it acts (FR-024):
#   - restart the FAILED layer first
#   - never restart a layer that is itself healthy
#   - a DEPENDENT layer may be restarted only when health evidence shows it
#     did not recover on its own after its failed dependency returned,
#     within $DependentGraceMinutes - never immediately, and never as a
#     blanket "restart everything downstream" reaction
#   - stop after $MaxRestartsBeforeAlert consecutive restarts of the same
#     layer and write an error-level log entry instead of continuing to
#     flood the log with actions that are not fixing anything
#
# Layer relationships in this script:
#   PrivateBinding and JobService are INDEPENDENT of each other (the whole
#     point of the feature-003 LAN-independence fix - see
#     start_web_service.ps1 and contracts/compute-link.md C4). Neither's
#     recovery ever touches the other.
#   Gpu has no safe automated remedy at this layer - a driver/hardware
#     fault is diagnosed and alerted, never "restarted" by this script.
#   AiEngine DEPENDS on Gpu. If AiEngine is unhealthy while Gpu is also
#     unhealthy, only Gpu's diagnostic fires - restarting ComfyUI while the
#     GPU itself is unusable would not fix anything. If Gpu recovers but
#     AiEngine remains unhealthy after $DependentGraceMinutes (a stale CUDA
#     context needing a nudge), THEN AiEngine's dependent-layer restart
#     fires - this is the one case in this script where a layer's own
#     health is not the sole trigger for acting on it.

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'health_chain.ps1') -EdgeTunnelAddress $EdgeTunnelAddress -WireGuardInterface $WireGuardInterface -WebPort $WebPort -ComfyBaseUrl $ComfyBaseUrl

function Get-State {
    if (Test-Path -LiteralPath $StateFile) {
        try { return Get-Content -LiteralPath $StateFile -Raw | ConvertFrom-Json } catch {}
    }
    return [pscustomobject]@{
        PrivateBindingRestartCount = 0
        PrivateBindingLastRestart  = $null
        JobServiceRestartCount     = 0
        JobServiceLastRestart      = $null
        GpuLastUnhealthyAt         = $null
        GpuRecoveredAt             = $null
        GpuLastAlertAt             = $null
        AiEngineRestartCount       = 0
        AiEngineLastRestart        = $null
    }
}

function Save-State($state) {
    $dir = Split-Path -Parent $StateFile
    if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    $state | ConvertTo-Json | Set-Content -LiteralPath $StateFile -Encoding UTF8
}

function Test-CooldownElapsed($lastRestart, [int]$minutes) {
    if ($null -eq $lastRestart -or $lastRestart -eq '') { return $true }
    return ([DateTimeOffset]::UtcNow - [DateTimeOffset]::Parse($lastRestart)) -gt (New-TimeSpan -Minutes $minutes)
}

function Write-Log($level, $message) {
    $line = "[{0:o}] [{1}] {2}" -f [DateTime]::UtcNow, $level, $message
    Write-Output $line
    $logDir = Join-Path $env:ProgramData 'Local3D'
    if (-not (Test-Path -LiteralPath $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
    Add-Content -LiteralPath (Join-Path $logDir 'watchdog.log') -Value $line
}

$state = Get-State
if (-not $state.PSObject.Properties['GpuRecoveredAt']) {
    $state | Add-Member -NotePropertyName GpuRecoveredAt -NotePropertyValue $null
}
$exitCode = 0

$privateBinding = Test-PrivateBindingHealth
$jobService = Test-JobServiceHealth
$gpu = Test-GpuHealth
$aiEngine = Test-AiEngineHealth

# --- Layer: PrivateBinding (independent of JobService) ---
if (-not $privateBinding.Healthy) {
    if ($state.PrivateBindingRestartCount -ge $MaxRestartsBeforeAlert) {
        Write-Log 'ERROR' "PrivateBinding unhealthy ($($privateBinding.Detail)) and restart limit ($MaxRestartsBeforeAlert) already reached. NOT restarting again - likely an external condition (e.g. outbound UDP/51820 blocked). Manual investigation required; see docs/operations/tunnel-setup.md."
        $exitCode = 1
    } elseif (-not (Test-CooldownElapsed $state.PrivateBindingLastRestart $CooldownMinutes)) {
        Write-Log 'WARN' "PrivateBinding unhealthy but within the $CooldownMinutes-minute cooldown of its last restart. Waiting."
    } else {
        Write-Log 'WARN' "PrivateBinding unhealthy ($($privateBinding.Detail)). Restarting $WireGuardServiceName only - JobService is unaffected by this layer."
        $state.PrivateBindingRestartCount = [int]$state.PrivateBindingRestartCount + 1
        $state.PrivateBindingLastRestart = [DateTime]::UtcNow.ToString('o')
        Save-State $state
        try {
            Restart-Service -Name $WireGuardServiceName -Force -ErrorAction Stop
            Write-Log 'INFO' "Restarted $WireGuardServiceName (attempt $($state.PrivateBindingRestartCount) of $MaxRestartsBeforeAlert)."
        } catch {
            Write-Log 'ERROR' "Failed to restart ${WireGuardServiceName}: $($_.Exception.Message)"
            $exitCode = 1
        }
    }
} elseif ([int]$state.PrivateBindingRestartCount -ne 0) {
    $state.PrivateBindingRestartCount = 0
    $state.PrivateBindingLastRestart = $null
}

# --- Layer: JobService (independent of PrivateBinding) ---
if (-not $jobService.Healthy) {
    if ($state.JobServiceRestartCount -ge $MaxRestartsBeforeAlert) {
        Write-Log 'ERROR' "JobService unhealthy ($($jobService.Detail)) and restart limit ($MaxRestartsBeforeAlert) already reached. NOT restarting again - investigate manually."
        $exitCode = 1
    } elseif (-not (Test-CooldownElapsed $state.JobServiceLastRestart $CooldownMinutes)) {
        Write-Log 'WARN' "JobService unhealthy but within the $CooldownMinutes-minute cooldown of its last restart. Waiting."
    } else {
        Write-Log 'WARN' "JobService unhealthy ($($jobService.Detail)). Restarting $WebServiceName only - PrivateBinding health, checked above, is independent of this."
        $state.JobServiceRestartCount = [int]$state.JobServiceRestartCount + 1
        $state.JobServiceLastRestart = [DateTime]::UtcNow.ToString('o')
        Save-State $state
        try {
            Restart-Service -Name $WebServiceName -Force -ErrorAction Stop
            Write-Log 'INFO' "Restarted $WebServiceName (attempt $($state.JobServiceRestartCount) of $MaxRestartsBeforeAlert)."
        } catch {
            Write-Log 'ERROR' "Failed to restart ${WebServiceName}: $($_.Exception.Message)"
            $exitCode = 1
        }
    }
} elseif ([int]$state.JobServiceRestartCount -ne 0) {
    $state.JobServiceRestartCount = 0
    $state.JobServiceLastRestart = $null
}

# --- Layer: Gpu (no safe automated remedy - diagnose and alert only) ---
if (-not $gpu.Healthy) {
    $state.GpuRecoveredAt = $null
    if (-not $state.GpuLastUnhealthyAt) {
        $state.GpuLastUnhealthyAt = [DateTime]::UtcNow.ToString('o')
    }
    if (Test-CooldownElapsed $state.GpuLastAlertAt $CooldownMinutes) {
        Write-Log 'ERROR' "Gpu unhealthy ($($gpu.Detail)). No automated remedy exists at this layer - a driver/hardware fault is not something a service restart can fix. Manual investigation (or a laptop reboot) required."
        $state.GpuLastAlertAt = [DateTime]::UtcNow.ToString('o')
    }
    $exitCode = 1
} elseif ($state.GpuLastUnhealthyAt) {
    Write-Log 'INFO' 'Gpu recovered.'
    $state.GpuLastUnhealthyAt = $null
    $state.GpuRecoveredAt = [DateTime]::UtcNow.ToString('o')
    $state.GpuLastAlertAt = $null
}

# --- Layer: AiEngine (DEPENDS on Gpu) ---
if (-not $gpu.Healthy) {
    # Gpu itself is unhealthy - do not act on AiEngine at all. Restarting
    # ComfyUI while the GPU is unusable would not fix anything and would
    # burn its own restart budget on a fault that lives one layer down.
    if (-not $aiEngine.Healthy) {
        Write-Log 'WARN' "AiEngine unhealthy ($($aiEngine.Detail)) but Gpu is also unhealthy - not acting on AiEngine until Gpu recovers."
    }
} elseif (-not $aiEngine.Healthy) {
    $withinGrace = $state.GpuRecoveredAt -and -not (Test-CooldownElapsed $state.GpuRecoveredAt $DependentGraceMinutes)
    if ($withinGrace) {
        Write-Log 'WARN' "AiEngine unhealthy ($($aiEngine.Detail)) shortly after Gpu recovered. Waiting up to $DependentGraceMinutes minutes for it to recover on its own before treating it as a dependent-layer restart."
    } elseif ($state.AiEngineRestartCount -ge $MaxRestartsBeforeAlert) {
        Write-Log 'ERROR' "AiEngine unhealthy ($($aiEngine.Detail)) and restart limit ($MaxRestartsBeforeAlert) already reached. NOT restarting again - investigate manually."
        $exitCode = 1
    } elseif (-not (Test-CooldownElapsed $state.AiEngineLastRestart $CooldownMinutes)) {
        Write-Log 'WARN' "AiEngine unhealthy but within the $CooldownMinutes-minute cooldown of its last restart. Waiting."
    } else {
        Write-Log 'WARN' "AiEngine unhealthy ($($aiEngine.Detail)) with Gpu healthy. Restarting $ComfyServiceName."
        $state.AiEngineRestartCount = [int]$state.AiEngineRestartCount + 1
        $state.AiEngineLastRestart = [DateTime]::UtcNow.ToString('o')
        Save-State $state
        try {
            Restart-Service -Name $ComfyServiceName -Force -ErrorAction Stop
            Write-Log 'INFO' "Restarted $ComfyServiceName (attempt $($state.AiEngineRestartCount) of $MaxRestartsBeforeAlert)."
        } catch {
            Write-Log 'ERROR' "Failed to restart ${ComfyServiceName}: $($_.Exception.Message)"
            $exitCode = 1
        }
    }
} elseif ([int]$state.AiEngineRestartCount -ne 0) {
    $state.AiEngineRestartCount = 0
    $state.AiEngineLastRestart = $null
}

Save-State $state

if ($exitCode -eq 0) {
    Write-Log 'INFO' 'All laptop-owned layers healthy or within recovery cooldown. No unbounded action taken.'
}
exit $exitCode
