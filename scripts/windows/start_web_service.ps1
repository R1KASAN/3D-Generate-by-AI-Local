[CmdletBinding()]
param(
    [string]$TunnelAddress = '10.10.0.2',
    [string]$EdgeTunnelAddress = '10.10.0.1',
    [ValidateRange(1, 65535)][int]$Port = 3000,
    [ValidateRange(1, 3600)][int]$MaxWaitSeconds = 300
)

# Waits for the WireGuard tunnel to be up before starting Next.js.
#
# web.xml binds Next.js to the tunnel address (10.10.0.2), not loopback.
# If Windows starts this service before the WireGuard tunnel interface has
# created that address, `next start --hostname 10.10.0.2` fails to bind and
# the service dies. A WinSW <depend> on the WireGuard tunnel service reduces
# the race but does not eliminate it - the tunnel service can report
# "started" before the interface address and a live handshake with the edge
# are actually in place. This script closes that gap the same way
# start_api_service.ps1 closes it for ComfyUI: poll for the real condition,
# not just "the dependency's service object exists".
#
# Two conditions are checked, in order:
#   1. The tunnel address is assigned to a local interface at all.
#   2. The edge (10.10.0.1) responds to a probe over that tunnel - proof of
#      a live, working tunnel, not just a WireGuard interface that exists
#      but has never completed a handshake (e.g. wrong keys, edge down,
#      border firewall not open on 51820/udp).
#
# See docs/operations/tunnel-setup.md for how to diagnose a timeout here.

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Wait-ForTunnelAddress {
    param([string]$Address, [datetime]$Deadline)
    while ([DateTime]::UtcNow -lt $Deadline) {
        $found = Get-NetIPAddress -AddressFamily IPv4 -IPAddress $Address -ErrorAction SilentlyContinue
        if ($null -ne $found) { return $true }
        Start-Sleep -Seconds 2
    }
    return $false
}

function Wait-ForEdgeReachable {
    param([string]$EdgeAddress, [datetime]$Deadline)
    while ([DateTime]::UtcNow -lt $Deadline) {
        try {
            # -Quiet suppresses exceptions and just returns a boolean; this
            # is an ICMP probe over the tunnel interface, not the public
            # internet, so it is unaffected by the edge's public firewall
            # policy (which correctly blocks unsolicited inbound ICMP).
            $ok = Test-Connection -TargetName $EdgeAddress -Count 1 -Quiet -ErrorAction SilentlyContinue
            if ($ok) { return $true }
        } catch {
            # Treated as "not yet reachable"; retry until the deadline.
        }
        Start-Sleep -Seconds 2
    }
    return $false
}

$deadline = [DateTime]::UtcNow.AddSeconds($MaxWaitSeconds)

Write-Output "Waiting for tunnel address $TunnelAddress to be assigned (timeout ${MaxWaitSeconds}s)..."
if (-not (Wait-ForTunnelAddress -Address $TunnelAddress -Deadline $deadline)) {
    throw "WireGuard tunnel address $TunnelAddress did not appear within $MaxWaitSeconds seconds. Is the WireGuard tunnel service running? See docs/operations/tunnel-setup.md."
}

Write-Output "Tunnel address present. Waiting for a live handshake with edge $EdgeTunnelAddress..."
if (-not (Wait-ForEdgeReachable -EdgeAddress $EdgeTunnelAddress -Deadline $deadline)) {
    throw "Edge $EdgeTunnelAddress was not reachable over the tunnel within $MaxWaitSeconds seconds. The interface exists but the tunnel is not actually working (check keys, edge status, and that the border firewall permits 51820/udp)."
}

Write-Output "Tunnel is live. Starting Next.js on ${TunnelAddress}:${Port}..."

$nodeExe = 'C:\Program Files\nodejs\node.exe'
$webDir = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..\apps\web')).Path
Set-Location -LiteralPath $webDir

& $nodeExe 'node_modules\next\dist\bin\next' start --hostname $TunnelAddress --port $Port
exit $LASTEXITCODE
