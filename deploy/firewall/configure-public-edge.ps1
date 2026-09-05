[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$PublicAddress,
    [Parameter(Mandatory = $true)][string]$CaddyPath,
    [Parameter(Mandatory = $true)][string[]]$CloudflareRange,
    [Parameter(Mandatory = $true)][string]$ManagementSourceCidr,
    [Parameter(Mandatory = $true)][ValidateRange(1, 65535)][int]$ManagementPort,
    [ValidateRange(1, 65535)][int]$WireGuardPort = 51820,
    [switch]$OwnerApproved
)

# Public-facing edge boundary for the Windows origin.
#
# The authoritative policy is specs/002-cloudflare-public-entry/contracts/
# port-policy.md. This script intentionally has no port-80 switch and no
# default management port. Cloudflare ranges must be fetched or supplied by
# deploy/firewall/cloudflare-ranges.ps1; an empty or invalid range list fails
# closed before any firewall rule is changed.

$ErrorActionPreference = 'Stop'

throw 'Retired inbound-era procedure: feature 003 uses an outbound connector and loopback origin pass-through. No firewall change performed. See docs/operations/tunnel-setup.md.'

if (-not $OwnerApproved) {
    throw 'Owner approval is required. Re-run with -OwnerApproved only after the Phase 2 owner and network gates are complete.'
}

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Administrator rights are required to configure the public edge boundary.'
}

$approvedPublicAddress = '161.200.90.4'
if ($PublicAddress -ne $approvedPublicAddress) {
    throw "PublicAddress must be exactly $approvedPublicAddress. Refusing any other address."
}
if (-not (Get-NetIPAddress -AddressFamily IPv4 -IPAddress $PublicAddress -ErrorAction SilentlyContinue)) {
    throw "$PublicAddress is not currently assigned to this machine. Refusing to configure an address this machine does not hold."
}
if (-not (Test-Path -LiteralPath $CaddyPath)) {
    throw "CaddyPath '$CaddyPath' does not exist. Install Caddy before applying the boundary."
}

$providerRanges = @($CloudflareRange | ForEach-Object { $_.Trim() } | Where-Object { $_ })
if ($providerRanges.Count -eq 0) {
    throw 'At least one current Cloudflare CIDR is required. Refusing to fall back to Any.'
}

function Test-Cidr($value) {
    $parts = $value.Split('/')
    if ($parts.Count -ne 2) { return $false }
    try {
        $address = [System.Net.IPAddress]::Parse($parts[0])
        $prefix = [int]$parts[1]
        $max = if ($address.AddressFamily -eq [System.Net.Sockets.AddressFamily]::InterNetwork) { 32 } else { 128 }
        return $prefix -ge 0 -and $prefix -le $max
    } catch { return $false }
}

$invalidRanges = @($providerRanges | Where-Object { -not (Test-Cidr $_) })
if ($invalidRanges.Count -gt 0) {
    throw "Invalid Cloudflare CIDR(s): $($invalidRanges -join ', '). Refusing to change existing rules."
}

$mgmtListening = Get-NetTCPConnection -State Listen -LocalPort $ManagementPort -ErrorAction SilentlyContinue
if (-not $mgmtListening) {
    throw "Nothing is listening on management port $ManagementPort. Prove the management path before applying default-deny."
}
Write-Output "Pre-flight passed: management listener exists on port $ManagementPort. Confirm access from $ManagementSourceCidr before ending this session."

$rulesToReplace = @(
    'Local3D Edge HTTPS',
    'Local3D Edge WireGuard',
    'Local3D Edge Management'
)
foreach ($name in $rulesToReplace) {
    Get-NetFirewallRule -DisplayName $name -ErrorAction SilentlyContinue | Remove-NetFirewallRule -ErrorAction SilentlyContinue
}

Set-NetFirewallProfile -All -Enabled True -DefaultInboundAction Block -DefaultOutboundAction Allow -ErrorAction Stop

New-NetFirewallRule -DisplayName 'Local3D Edge HTTPS' `
    -Description 'Public HTTPS entry; Caddy only; Cloudflare ranges only.' `
    -Direction Inbound -Action Allow -Enabled True -Profile Any `
    -Protocol TCP -LocalAddress $PublicAddress -LocalPort 443 `
    -RemoteAddress $providerRanges -Program $CaddyPath | Out-Null

New-NetFirewallRule -DisplayName 'Local3D Edge WireGuard' `
    -Description 'WireGuard tunnel; peer authentication is by public key.' `
    -Direction Inbound -Action Allow -Enabled True -Profile Any `
    -Protocol UDP -LocalAddress $PublicAddress -LocalPort $WireGuardPort `
    -RemoteAddress Any | Out-Null

New-NetFirewallRule -DisplayName 'Local3D Edge Management' `
    -Description 'Administrative access restricted to the approved management source.' `
    -Direction Inbound -Action Allow -Enabled True -Profile Any `
    -Protocol TCP -LocalPort $ManagementPort `
    -RemoteAddress $ManagementSourceCidr | Out-Null

foreach ($blockedPort in 80, 3000, 8000, 8188, 3389, 2019) {
    $blockName = "Local3D Edge Explicit Block $blockedPort"
    Get-NetFirewallRule -DisplayName $blockName -ErrorAction SilentlyContinue | Remove-NetFirewallRule -ErrorAction SilentlyContinue
    New-NetFirewallRule -DisplayName $blockName `
        -Description 'Defense-in-depth explicit block; default-deny already covers this port.' `
        -Direction Inbound -Action Block -Enabled True -Profile Any `
        -Protocol TCP -LocalPort $blockedPort | Out-Null
}

Write-Output "Configured public edge boundary for $PublicAddress`: 443/tcp from Cloudflare ranges, $WireGuardPort/udp from Any, management port $ManagementPort from $ManagementSourceCidr, and explicit blocks including 80/tcp."
Write-Output 'IMPORTANT: open a NEW connection to confirm management access before ending this session.'
