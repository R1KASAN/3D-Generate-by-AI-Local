[CmdletBinding()]
param(
    [ValidateRange(1, 65535)][int]$Port = 3000
)

# Starts Next.js on loopback, unconditionally.
#
# Feature 002 bound this service to the WireGuard tunnel address and made it
# wait for a live handshake before starting, because under that architecture
# the tunnel address WAS this service's public bind address. Feature 003
# moves the public entry to the approved origin (see
# specs/003-outbound-tunnel-entry/contracts/compute-link.md C4), so that
# wait is now a regression: if WireGuard is down when this service starts,
# waiting for it would take the LAN-only workflow down too, violating
# FR-023a/FR-023d/FR-037.
#
# This service now starts immediately on 127.0.0.1. The LAN reaches it
# through the existing host port-forward (configure_lan_boundary.ps1), and
# the approved origin reaches the same loopback listener over the WireGuard
# tunnel address once that binding is up - see docs/operations/tunnel-setup.md
# for how the private-binding port-forward is configured. Losing that
# binding degrades only the public path; it never stops this service from
# starting or serving the LAN.

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Write-Output "Starting Next.js on 127.0.0.1:${Port} (no private-binding wait)..."

$nodeExe = 'C:\Program Files\nodejs\node.exe'
$webDir = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..\apps\web')).Path
Set-Location -LiteralPath $webDir

& $nodeExe 'node_modules\next\dist\bin\next' start --hostname 127.0.0.1 --port $Port
exit $LASTEXITCODE
