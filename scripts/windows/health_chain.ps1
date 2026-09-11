<#
.SYNOPSIS
    Independent health probes for the feature-004 single Notebook.

    All local application probes use loopback. Public-route probes are
    optional and only run when an operator supplies the current Quick Tunnel
    URL; the URL is never persisted by this script.
##>
[CmdletBinding()]
param(
    [ValidateRange(1, 65535)][int]$CaddyPort = 8080,
    [ValidateRange(1, 65535)][int]$WebPort = 3000,
    [ValidateRange(1, 65535)][int]$ApiPort = 8000,
    [ValidateRange(1, 65535)][int]$ComfyPort = 8188,
    [string]$WorkflowManifest = 'workflows\hunyuan3d\workflow-manifest.json',
    [string]$QuickTunnelUrl,
    [string]$StableApiUrl,
    [switch]$Feature005,
    [switch]$Json
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Probe-Http([string]$Uri) {
    try { Invoke-WebRequest -UseBasicParsing -Uri $Uri -TimeoutSec 5 -ErrorAction Stop | Out-Null; return $true }
    catch { return $false }
}
function Probe-HttpWithHost([string]$Uri, [string]$HostName) {
    try { Invoke-WebRequest -UseBasicParsing -Uri $Uri -Headers @{ Host = $HostName } -TimeoutSec 5 -ErrorAction Stop | Out-Null; return $true }
    catch { return $false }
}
function Test-CaddyHealth { [pscustomobject]@{ Healthy = (Probe-Http "http://127.0.0.1:${CaddyPort}/api/v1/health/live"); Detail = "loopback Caddy :$CaddyPort" } }
function Test-WebHealth { [pscustomobject]@{ Healthy = (Probe-Http "http://127.0.0.1:${CaddyPort}/"); Detail = "frontend through Caddy" } }
function Test-ApiHealth { [pscustomobject]@{ Healthy = (Probe-Http "http://127.0.0.1:${CaddyPort}/api/v1/health/live"); Detail = "FastAPI through /api/*" } }
function Test-StorageHealth { try { $root = Split-Path -Parent $WorkflowManifest; [pscustomobject]@{ Healthy = (Test-Path -LiteralPath $root); Detail = 'storage/config path available' } } catch { [pscustomobject]@{ Healthy = $false; Detail = 'storage probe failed' } } }
function Test-WorkflowHealth { [pscustomobject]@{ Healthy = (Test-Path -LiteralPath $WorkflowManifest); Detail = 'workflow manifest present' } }
function Test-ComfyHealth { [pscustomobject]@{ Healthy = (Probe-Http "http://127.0.0.1:${ComfyPort}/system_stats"); Detail = "ComfyUI loopback :$ComfyPort" } }
function Test-GpuHealth {
    $tool = Get-Command nvidia-smi -ErrorAction SilentlyContinue
    if (-not $tool) { return [pscustomobject]@{ Healthy = $false; Detail = 'nvidia-smi unavailable' } }
    try { & $tool.Source --query-gpu=name --format=csv,noheader 2>$null | Out-Null; [pscustomobject]@{ Healthy = ($LASTEXITCODE -eq 0); Detail = 'GPU driver probe' } }
    catch { [pscustomobject]@{ Healthy = $false; Detail = 'GPU probe failed' } }
}
function Test-QuickTunnelHealth { if (-not $QuickTunnelUrl) { return [pscustomobject]@{ Healthy = $false; Detail = 'Quick Tunnel URL not supplied' } }; [pscustomobject]@{ Healthy = (Probe-Http ($QuickTunnelUrl.TrimEnd('/') + '/')); Detail = 'temporary public route' } }
function Test-PublicRouteHealth { Test-QuickTunnelHealth }
function Test-ListenerBoundaryHealth {
    $ports = @($WebPort, $ApiPort, $CaddyPort, $ComfyPort)
    $bad = @()
    foreach ($port in $ports) {
        $connections = Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue
        if ($connections | Where-Object { $_.LocalAddress -notin @('127.0.0.1', '::1') }) { $bad += $port }
    }
    [pscustomobject]@{ Healthy = ($bad.Count -eq 0); Detail = if ($bad.Count) { 'non-loopback listener detected' } else { 'application ports loopback-only' } }
}
function Test-ProcessBoundaryHealth {
    $definitionName = if ($Feature005) { 'nginx.xml' } else { 'caddy.xml' }
    $definition = Join-Path (Get-Location) "deploy\windows\services\$definitionName"
    if ($Feature005) {
        $nginx = Get-Service -Name 'Local3D-Nginx' -ErrorAction SilentlyContinue
        $caddy = Get-Service -Name 'Local3D-Caddy' -ErrorAction SilentlyContinue
        $healthy = (Test-Path -LiteralPath $definition) -and $null -ne $nginx -and $nginx.Status -eq 'Running' -and ($null -eq $caddy -or $caddy.Status -ne 'Running')
        return [pscustomobject]@{ Healthy = $healthy; Detail = "Nginx service running and Caddy not running; definition=$definitionName" }
    }
    [pscustomobject]@{ Healthy = (Test-Path -LiteralPath $definition); Detail = "single-machine $definitionName present" }
}

if ($Feature005) {
    $apiOriginHealthy = $false
    $apiDetail = 'stable API URL not supplied'
    if ($StableApiUrl) {
        $apiOriginHealthy = Probe-Http ($StableApiUrl.TrimEnd('/') + '/health/live')
        $apiDetail = 'named Tunnel stable API probe'
    }
    $results = [ordered]@{
        Nginx = [pscustomobject]@{ Healthy = ((Test-ProcessBoundaryHealth).Healthy -and (Probe-HttpWithHost "http://127.0.0.1:${CaddyPort}/api/v1/health/live" 'mango74-api.mangosgo.com')); Detail = "loopback Nginx :$CaddyPort" }
        Api = Test-ApiHealth
        Storage = Test-StorageHealth
        Workflow = Test-WorkflowHealth
        ComfyUI = Test-ComfyHealth
        GPU = Test-GpuHealth
        NamedTunnel = [pscustomobject]@{ Healthy = $false; Detail = 'named Tunnel service is checked by verify_named_tunnel.ps1' }
        StablePublicApi = [pscustomobject]@{ Healthy = $apiOriginHealthy; Detail = $apiDetail }
        ListenerBoundary = Test-ListenerBoundaryHealth
        ProcessBoundary = Test-ProcessBoundaryHealth
    }
} else {
    $results = [ordered]@{
        Caddy = Test-CaddyHealth
        Web = Test-WebHealth
        Api = Test-ApiHealth
        Storage = Test-StorageHealth
        Workflow = Test-WorkflowHealth
        ComfyUI = Test-ComfyHealth
        GPU = Test-GpuHealth
        QuickTunnel = Test-QuickTunnelHealth
        PublicRoute = Test-PublicRouteHealth
        ListenerBoundary = Test-ListenerBoundaryHealth
        ProcessBoundary = Test-ProcessBoundaryHealth
    }
}
if ($Json) { $results | ConvertTo-Json -Depth 4; exit 0 }
$failed = 0
foreach ($name in $results.Keys) {
    $result = $results[$name]
    $state = if ($result.Healthy) { 'HEALTHY' } else { 'UNHEALTHY' }
    if (-not $result.Healthy) { $failed++ }
    Write-Output "[$name] $state - $($result.Detail)"
}
exit $(if ($failed -eq 0) { 0 } else { 1 })
