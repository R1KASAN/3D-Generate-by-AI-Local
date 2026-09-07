[CmdletBinding()]
param(
    [string]$HealthScript = (Join-Path $PSScriptRoot 'health_chain.ps1'),
    [string]$StatePath = (Join-Path $env:ProgramData 'Local3D\quick-tunnel-watchdog.json')
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Feature 004 deliberately has no automatic tunnel, WireGuard, DNS, or
# firewall mutation. This watchdog is diagnostic only; an operator owns the
# Quick Tunnel session and uses stop_quick_tunnel.ps1 to end it.
$probe = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $HealthScript -Json 2>&1 | Out-String
$directory = Split-Path -Parent $StatePath
New-Item -ItemType Directory -Path $directory -Force | Out-Null
@{ checked_at = [DateTime]::UtcNow.ToString('o'); health = $probe } |
    ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $StatePath -Encoding utf8
Write-Output 'PASS: diagnostic-only watchdog completed; no tunnel, DNS, firewall, or service mutation was performed.'
