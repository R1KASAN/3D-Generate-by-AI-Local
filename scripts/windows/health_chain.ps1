<#
.SYNOPSIS
    Layered health probes for the GPU-laptop-owned layers of the feature-003
    health chain (contracts/health-chain.md H1).

.DESCRIPTION
    Implements one independently callable function per laptop-owned layer:
    private binding, job service, AI engine, and GPU. Each function probes
    only what it owns - none of them infer their result from another
    layer's output (FR-023c). The GPU layer specifically uses nvidia-smi
    rather than the AI engine's own status endpoint, per the decision in
    evidence/public-deployment/health-probe-decision.md (T027): this lets
    GPU be reported independently of - and, when run in that order, ahead
    of - the AI engine, so a driver/hardware fault is distinguishable from
    an application-only fault.

    The origin-owned layers (provider edge, origin/connector) are probed by
    a separate, OS-independent mechanism on the approved origin - see
    contracts/origin-entry.md O7 and research.md R1. This script only
    covers what the laptop can observe about itself.

.PARAMETER EdgeTunnelAddress
    The origin's WireGuard tunnel address, used for the private-binding
    handshake/reachability check.

.PARAMETER WireGuardInterface
    The WireGuard interface name for the private binding.

.PARAMETER WebPort
    The loopback port the job service (Next.js) listens on.

.PARAMETER ComfyBaseUrl
    The loopback base URL for the ComfyUI AI engine.

.PARAMETER HandshakeFreshSeconds
    Maximum age, in seconds, of the private binding's last handshake to be
    considered live.

.EXAMPLE
    pwsh scripts/windows/health_chain.ps1 -All
#>
[CmdletBinding()]
param(
    [string]$EdgeTunnelAddress = '10.10.0.1',
    [string]$WireGuardInterface = 'upstream',
    [ValidateRange(1, 65535)][int]$WebPort = 3000,
    [string]$ComfyBaseUrl = 'http://127.0.0.1:8188',
    [ValidateRange(1, 3600)][int]$HandshakeFreshSeconds = 180,
    [switch]$All
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Resolve-WireGuardExecutable {
    $candidate = Get-Command 'wg.exe' -ErrorAction SilentlyContinue
    if ($candidate) { return $candidate.Source }
    $installed = Join-Path ${env:ProgramFiles} 'WireGuard\wg.exe'
    if (Test-Path -LiteralPath $installed) { return $installed }
    return $null
}

function Test-PrivateBindingHealth {
    # Owns: the WireGuard link to the approved origin. A recent handshake
    # is the only trustworthy signal - an assigned interface address alone
    # can exist even when the tunnel is not actually passing traffic.
    $wg = Resolve-WireGuardExecutable
    if (-not $wg) {
        return [pscustomobject]@{ Healthy = $false; Detail = 'wg CLI not found' }
    }
    try {
        $output = & $wg show $WireGuardInterface latest-handshakes 2>$null
        $now = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
        foreach ($line in $output) {
            $fields = $line -split '\s+'
            if ($fields.Count -ge 2) {
                [long]$timestamp = 0
                if ([long]::TryParse($fields[1], [ref]$timestamp) -and $timestamp -gt 0) {
                    $age = $now - $timestamp
                    if ($age -ge 0 -and $age -le $HandshakeFreshSeconds) {
                        return [pscustomobject]@{ Healthy = $true; Detail = "handshake age ${age}s" }
                    }
                }
            }
        }
        return [pscustomobject]@{ Healthy = $false; Detail = 'no handshake within freshness window' }
    } catch {
        return [pscustomobject]@{ Healthy = $false; Detail = "wg query failed: $($_.Exception.Message)" }
    }
}

function Test-JobServiceHealth {
    # Owns: the Next.js job service, which now starts independently of the
    # private binding (FR-023a). Checked on loopback only - this layer's
    # health has nothing to do with whether the tunnel is up.
    try {
        $listening = Get-NetTCPConnection -State Listen -LocalAddress 127.0.0.1 -LocalPort $WebPort -ErrorAction SilentlyContinue
        if ($listening) {
            return [pscustomobject]@{ Healthy = $true; Detail = "listening on 127.0.0.1:$WebPort" }
        }
        return [pscustomobject]@{ Healthy = $false; Detail = "not listening on 127.0.0.1:$WebPort" }
    } catch {
        return [pscustomobject]@{ Healthy = $false; Detail = "probe failed: $($_.Exception.Message)" }
    }
}

function Test-GpuHealth {
    # Owns: GPU hardware/driver presence, probed via nvidia-smi at the OS
    # level. Deliberately does NOT call the AI engine's /system_stats -
    # doing so would make this layer's health derive from a layer it must
    # remain independent of (FR-023c), and would defeat the whole point of
    # the T027 decision to order GPU ahead of the engine.
    $nvidiaSmi = Get-Command 'nvidia-smi' -ErrorAction SilentlyContinue
    if (-not $nvidiaSmi) {
        return [pscustomobject]@{ Healthy = $false; Detail = 'nvidia-smi not found on PATH' }
    }
    try {
        $output = & nvidia-smi --query-gpu=name,driver_version --format=csv,noheader 2>$null
        if ($LASTEXITCODE -eq 0 -and $output) {
            return [pscustomobject]@{ Healthy = $true; Detail = ($output -join '; ') }
        }
        return [pscustomobject]@{ Healthy = $false; Detail = "nvidia-smi exited $LASTEXITCODE" }
    } catch {
        return [pscustomobject]@{ Healthy = $false; Detail = "nvidia-smi invocation failed: $($_.Exception.Message)" }
    }
}

function Test-AiEngineHealth {
    # Owns: ComfyUI's own readiness - queue state, model load - which only
    # its /system_stats endpoint can report. This is legitimate here (the
    # engine's own health necessarily comes from the engine); it would only
    # be a violation if the GPU layer above depended on this one instead of
    # the reverse.
    try {
        $response = Invoke-RestMethod -Uri "$ComfyBaseUrl/system_stats" -TimeoutSec 5 -ErrorAction Stop
        if ($response) {
            return [pscustomobject]@{ Healthy = $true; Detail = 'system_stats responded' }
        }
        return [pscustomobject]@{ Healthy = $false; Detail = 'empty system_stats response' }
    } catch {
        return [pscustomobject]@{ Healthy = $false; Detail = "system_stats unreachable: $($_.Exception.Message)" }
    }
}

if ($All -or $MyInvocation.InvocationName -ne '.') {
    # Report in the decided order: private binding -> job service -> GPU -> AI engine.
    $results = [ordered]@{
        PrivateBinding = Test-PrivateBindingHealth
        JobService     = Test-JobServiceHealth
        Gpu            = Test-GpuHealth
        AiEngine       = Test-AiEngineHealth
    }
    foreach ($layer in $results.Keys) {
        $result = $results[$layer]
        $state = if ($result.Healthy) { 'HEALTHY' } else { 'UNHEALTHY' }
        Write-Output "[$layer] $state - $($result.Detail)"
    }
}
