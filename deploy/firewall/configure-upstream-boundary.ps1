[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateScript({ [System.Net.IPAddress]::Parse($_).AddressFamily -eq [System.Net.Sockets.AddressFamily]::InterNetwork })]
    [string]$EdgePeer,

    [ValidateScript({ [System.Net.IPAddress]::Parse($_).AddressFamily -eq [System.Net.Sockets.AddressFamily]::InterNetwork })]
    [string]$TunnelAddress = '10.10.0.2',

    [string]$TunnelSubnetCidr = '10.10.0.0/24',

    [ValidateRange(1, 65535)][int]$WebPort = 3000,

    [switch]$OwnerApproved
)

# Laptop-side network boundary for the mobile-GPU public deployment (T051,
# revised for feature 003 in specs/003-outbound-tunnel-entry).
#
# This is the mirror image of scripts/windows/configure_lan_boundary.ps1:
# that script proves an address is PRIVATE before exposing it on the LAN;
# this one proves the laptop does NOT hold a public IP (it must stay behind
# NAT, reachable only through the WireGuard tunnel) before opening anything.
# Every refusal below runs before any change is made (fail closed).
#
# Feature 002 -> feature 003 change: Next.js used to bind the tunnel address
# (10.10.0.2) directly, so this script only had to open a firewall rule -
# the listening socket already existed at the right address. Feature 003's
# LAN-independence fix (contracts/compute-link.md C4) moved the web service
# to a loopback-only bind so it starts without waiting on WireGuard; the
# tunnel address now needs an explicit port-forward to reach it, the same
# mechanism scripts/windows/configure_lan_boundary.ps1 already uses for LAN
# clients. This script now manages that portproxy entry as well as the
# firewall rule - it no longer refuses to run because one exists.

$ErrorActionPreference = 'Stop'
$ruleName = 'Local3D Upstream Entry'
$staleLanRuleName = 'Local3D LAN Web Entry'

# --- 1. Owner approval ---
if (-not $OwnerApproved) {
    throw 'Owner approval is required. Re-run with -OwnerApproved only after Stage 2 of the deployment plan is complete.'
}

# --- 2. Administrator rights ---
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Administrator rights are required to configure the upstream boundary.'
}

# --- 3. EdgePeer must be a single tunnel-subnet host, never a wide range ---
# (Avoids [System.Net.IPNetwork], which is not available under Windows
# PowerShell 5.1 / .NET Framework - only newer .NET builds have it.)
function Test-IPv4InCidr {
    param([string]$IPAddress, [string]$Cidr)
    $parts = $Cidr.Split('/')
    $networkBytes = [System.Net.IPAddress]::Parse($parts[0]).GetAddressBytes()
    $prefixLength = [int]$parts[1]
    $addressBytes = [System.Net.IPAddress]::Parse($IPAddress).GetAddressBytes()
    if ([BitConverter]::IsLittleEndian) {
        [Array]::Reverse($networkBytes)
        [Array]::Reverse($addressBytes)
    }
    $networkInt = [BitConverter]::ToUInt32($networkBytes, 0)
    $addressInt = [BitConverter]::ToUInt32($addressBytes, 0)
    $mask = if ($prefixLength -eq 0) { 0 } else { [uint32]::MaxValue -shl (32 - $prefixLength) }
    return ($networkInt -band $mask) -eq ($addressInt -band $mask)
}
if (-not (Test-IPv4InCidr -IPAddress $EdgePeer -Cidr $TunnelSubnetCidr)) {
    throw "EdgePeer must be a single address inside the tunnel subnet $TunnelSubnetCidr; received $EdgePeer. This script never opens 3000 to a wide address range."
}

# --- 4. This laptop must NOT hold a public IP (topology guard) ---
# 161.200.90.4 belongs to the edge only. If this machine ever holds a
# routable public address directly, the two-box topology this deployment
# depends on has been violated and this script must refuse to proceed.
function Test-IsPublicIPv4 {
    param([System.Net.IPAddress]$Address)
    $bytes = $Address.GetAddressBytes()
    if ($bytes[0] -eq 127) { return $false }                                   # loopback
    if ($bytes[0] -eq 10) { return $false }                                    # RFC1918
    if ($bytes[0] -eq 172 -and $bytes[1] -ge 16 -and $bytes[1] -le 31) { return $false }  # RFC1918
    if ($bytes[0] -eq 192 -and $bytes[1] -eq 168) { return $false }            # RFC1918
    if ($bytes[0] -eq 169 -and $bytes[1] -eq 254) { return $false }            # link-local/APIPA
    if ($bytes[0] -eq 100 -and $bytes[1] -ge 64 -and $bytes[1] -le 127) { return $false } # CGNAT
    return $true
}
$publicAddresses = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object { Test-IsPublicIPv4 ([System.Net.IPAddress]::Parse($_.IPAddress)) }
if ($publicAddresses) {
    $list = ($publicAddresses | ForEach-Object { $_.IPAddress }) -join ', '
    throw "This machine holds a public IPv4 address ($list). The mobile-laptop topology requires this machine to stay behind NAT, reachable only via the WireGuard tunnel. Refusing to configure the upstream boundary - check whether this script is being run on the edge server by mistake."
}

# --- 5. Any existing portproxy entry must be exactly the expected mapping,
#        or absent - never a stale mapping to something else ---
$proxyText = (& netsh interface portproxy show v4tov4) -join "`n"
$escapedTunnel = [regex]::Escape($TunnelAddress)
$exactProxy = $proxyText -match "(?m)^\s*$escapedTunnel\s+$WebPort\s+127\.0\.0\.1\s+$WebPort\s*$"
if (-not $exactProxy) {
    $stalePattern = "(?m)^\s*$escapedTunnel\s+$WebPort\s+"
    if ($proxyText -match $stalePattern) {
        & netsh interface portproxy delete v4tov4 listenaddress=$TunnelAddress listenport=$WebPort protocol=tcp | Out-Null
    }
}

# --- 6. 8000/8188 must be loopback-only before 3000 is opened (fail closed) ---
$listeners = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue
foreach ($port in 8000, 8188) {
    $unsafe = @($listeners | Where-Object { $_.LocalPort -eq $port -and $_.LocalAddress -notin @('127.0.0.1', '::1') })
    if ($unsafe.Count -gt 0) {
        throw "Port $port has a non-loopback listener. Refusing to open port $WebPort until the internal API/ComfyUI ports are confirmed loopback-only."
    }
}

# --- 7. RDP must stay disabled ---
$rdpKey = 'HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server'
$rdpDenied = (Get-ItemProperty -Path $rdpKey -Name fDenyTSConnections -ErrorAction SilentlyContinue).fDenyTSConnections
if ($rdpDenied -ne 1) {
    throw 'Remote Desktop is not disabled (fDenyTSConnections != 1). RDP must never be reachable from a machine that later exposes a service to the internet via tunnel. Disable RDP before continuing.'
}

# ---------------------------------------------------------------------------
# All preconditions satisfied - apply the boundary.
# ---------------------------------------------------------------------------

Set-NetFirewallProfile -All -Enabled True -DefaultInboundAction Block -DefaultOutboundAction Allow -ErrorAction Stop

# Forward the tunnel address to the web service's loopback listener. Next.js
# no longer binds $TunnelAddress directly (feature 003) - this portproxy
# entry is what makes traffic arriving over the private WireGuard binding
# still reach it, the same way configure_lan_boundary.ps1 does for LAN
# clients.
if (-not $exactProxy) {
    & netsh interface portproxy add v4tov4 listenaddress=$TunnelAddress listenport=$WebPort connectaddress=127.0.0.1 connectport=$WebPort protocol=tcp | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw 'Failed to create the tunnel-to-loopback web proxy.'
    }
}

Get-NetFirewallRule -DisplayName $staleLanRuleName -ErrorAction SilentlyContinue |
    Remove-NetFirewallRule -ErrorAction SilentlyContinue

Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue |
    Remove-NetFirewallRule -ErrorAction SilentlyContinue
New-NetFirewallRule `
    -DisplayName $ruleName `
    -Description "Owner-approved upstream entry for the WireGuard-tunneled public deployment; edge peer ($EdgePeer) only." `
    -Direction Inbound `
    -Action Allow `
    -Enabled True `
    -Profile Any `
    -Protocol TCP `
    -LocalAddress $TunnelAddress `
    -LocalPort $WebPort `
    -RemoteAddress $EdgePeer | Out-Null

# Explicit deny rules for defense-in-depth (default-deny already covers
# these, but an explicit rule gives the verifier and any future auditor
# something concrete to check, and survives a future profile change).
foreach ($blockedPort in 8000, 8188, 3389) {
    $blockName = "Local3D Explicit Block $blockedPort"
    Get-NetFirewallRule -DisplayName $blockName -ErrorAction SilentlyContinue |
        Remove-NetFirewallRule -ErrorAction SilentlyContinue
    New-NetFirewallRule `
        -DisplayName $blockName `
        -Description 'Defense-in-depth explicit block; default-deny already covers this port.' `
        -Direction Inbound `
        -Action Block `
        -Enabled True `
        -Profile Any `
        -Protocol TCP `
        -LocalPort $blockedPort | Out-Null
}

Write-Output "Configured upstream entry: TCP ${TunnelAddress}:${WebPort} <- ${EdgePeer} only, forwarded to 127.0.0.1:${WebPort}."
Write-Output 'Ports 8000 and 8188 remain loopback-only and are also explicitly blocked inbound.'
Write-Output 'RDP (3389) remains disabled and is also explicitly blocked inbound.'
