[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$PublicAddress,
    [Parameter(Mandatory = $true)][string]$CaddyPath,

    # Management access (SSH or RDP to administer the edge itself). MUST be
    # decided (Stage 0.1 of the deployment plan) and passed explicitly -
    # there is no default, because guessing wrong here can lock the
    # operator out of the box entirely once this script finishes.
    [Parameter(Mandatory = $true)][string]$ManagementSourceCidr,
    [ValidateRange(1, 65535)][int]$ManagementPort = 22,

    [ValidateRange(1, 65535)][int]$WireGuardPort = 51820,
    [switch]$EnableHttp = $true,
    [switch]$OwnerApproved
)

# Public-facing edge boundary (T088, edge half).
#
# This is the Windows/PowerShell variant. If the edge server turns out to
# run Linux (Stage 0.2 of the deployment plan decides this), an equivalent
# nftables/ufw ruleset must be written instead - see
# deploy/firewall/README.md once that decision is made. The port policy
# table in docs/operations/public-cutover.md is authoritative for either
# implementation; do not let the two drift apart.
#
# Ports opened here (see the plan's single port-policy table):
#   443/tcp   - HTTPS (Caddy only, enforced via -Program)
#   80/tcp    - ACME HTTP-01 + redirect only (Caddy only)
#   51820/udp - WireGuard, open to Any - see the note below on why
#   $ManagementPort/tcp - admin access, restricted to $ManagementSourceCidr
#
# Everything else is denied by the default-deny profile, with explicit
# block rules added for the ports operators most often assume are open.

$ErrorActionPreference = 'Stop'

# --- 1. Owner approval ---
if (-not $OwnerApproved) {
    throw 'Owner approval is required. Re-run with -OwnerApproved only after Stage 2 of the deployment plan is complete.'
}

# --- 2. Administrator rights ---
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Administrator rights are required to configure the public edge boundary.'
}

# --- 3. Hard-coded address guard: 161.200.90.4 ONLY, never .3 ---
# .3 is allocated to a different purpose entirely and must never be
# configured, forwarded, or probed by anything in this repository.
$approvedPublicAddress = '161.200.90.4'
if ($PublicAddress -ne $approvedPublicAddress) {
    throw "PublicAddress must be exactly $approvedPublicAddress. Received '$PublicAddress'. This is a hard-coded refusal, not a configuration option - only the address named in evidence/public-deployment/owner-gate.md is approved for use anywhere in this repository."
}
if (-not (Get-NetIPAddress -AddressFamily IPv4 -IPAddress $PublicAddress -ErrorAction SilentlyContinue)) {
    throw "$PublicAddress is not currently assigned to this machine. Refusing to configure firewall rules for an address this machine does not hold."
}

# --- 4. Pre-flight: confirm the chosen management path is actually usable
#         BEFORE any rule that could remove access is applied ---
Write-Output "Pre-flight: confirming management access via ${ManagementSourceCidr} on port ${ManagementPort} before applying any deny-by-default changes..."
$mgmtListening = Get-NetTCPConnection -State Listen -LocalPort $ManagementPort -ErrorAction SilentlyContinue
if (-not $mgmtListening) {
    throw "Nothing is listening on management port $ManagementPort yet. Configure and start the management service (e.g. sshd) FIRST, confirm you can reach it, and only then re-run this script. Applying firewall rules before that risks locking the operator out of this edge server entirely."
}
Write-Output "Management port $ManagementPort has a listener. Proceeding - but you must still manually confirm you can reach it from $ManagementSourceCidr before ending this session."

# --- 5. Caddy binary must exist and will be the only process allowed on 443/80 ---
if (-not (Test-Path -LiteralPath $CaddyPath)) {
    throw "CaddyPath '$CaddyPath' does not exist. Install Caddy first (Stage 3 of the deployment plan)."
}

# ---------------------------------------------------------------------------
# Apply the boundary.
# ---------------------------------------------------------------------------

Set-NetFirewallProfile -All -Enabled True -DefaultInboundAction Block -DefaultOutboundAction Allow -ErrorAction Stop

$rulesToReplace = @(
    'Local3D Edge HTTPS',
    'Local3D Edge HTTP (ACME/redirect)',
    'Local3D Edge WireGuard',
    'Local3D Edge Management'
)
foreach ($name in $rulesToReplace) {
    Get-NetFirewallRule -DisplayName $name -ErrorAction SilentlyContinue | Remove-NetFirewallRule -ErrorAction SilentlyContinue
}

New-NetFirewallRule -DisplayName 'Local3D Edge HTTPS' `
    -Description 'Public HTTPS entry; Caddy only.' `
    -Direction Inbound -Action Allow -Enabled True -Profile Any `
    -Protocol TCP -LocalAddress $PublicAddress -LocalPort 443 `
    -RemoteAddress Any -Program $CaddyPath | Out-Null

if ($EnableHttp) {
    New-NetFirewallRule -DisplayName 'Local3D Edge HTTP (ACME/redirect)' `
        -Description 'ACME HTTP-01 challenge and HTTPS redirect only; Caddy only.' `
        -Direction Inbound -Action Allow -Enabled True -Profile Any `
        -Protocol TCP -LocalAddress $PublicAddress -LocalPort 80 `
        -RemoteAddress Any -Program $CaddyPath | Out-Null
}

# 51820/udp is deliberately open to Any, not restricted by source address:
# the laptop's source IP changes every time it moves networks, so an
# allowlist would defeat the entire point of the mobile-GPU design.
# Security here comes from WireGuard's own public-key authentication -
# an unauthenticated packet is silently dropped, not merely denied, so
# a port scan cannot even confirm the port is "open" in the usual sense.
New-NetFirewallRule -DisplayName 'Local3D Edge WireGuard' `
    -Description 'WireGuard tunnel to the mobile GPU laptop. Open to Any by design; authentication is per-packet via WireGuard public keys, not source-IP filtering.' `
    -Direction Inbound -Action Allow -Enabled True -Profile Any `
    -Protocol UDP -LocalAddress $PublicAddress -LocalPort $WireGuardPort `
    -RemoteAddress Any | Out-Null

New-NetFirewallRule -DisplayName 'Local3D Edge Management' `
    -Description 'Administrative access to the edge itself, restricted to the approved management source.' `
    -Direction Inbound -Action Allow -Enabled True -Profile Any `
    -Protocol TCP -LocalPort $ManagementPort `
    -RemoteAddress $ManagementSourceCidr | Out-Null

# Explicit deny rules for the ports operators most often assume the NAT
# used to hide, now that this box holds a real public IP directly.
foreach ($blockedPort in 3000, 8000, 8188, 3389, 2019) {
    $blockName = "Local3D Edge Explicit Block $blockedPort"
    Get-NetFirewallRule -DisplayName $blockName -ErrorAction SilentlyContinue | Remove-NetFirewallRule -ErrorAction SilentlyContinue
    New-NetFirewallRule -DisplayName $blockName `
        -Description 'Defense-in-depth explicit block; default-deny already covers this port.' `
        -Direction Inbound -Action Block -Enabled True -Profile Any `
        -Protocol TCP -LocalPort $blockedPort | Out-Null
}

Write-Output "Configured public edge boundary for $PublicAddress`: 443/tcp + 80/tcp (Caddy only), $WireGuardPort/udp (Any, key-authenticated), $ManagementPort/tcp (from $ManagementSourceCidr only)."
Write-Output 'IMPORTANT: before ending this session, open a NEW connection to confirm management access still works. Do not close your current session until you have verified this.'
