[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateScript({ [System.Net.IPAddress]::Parse($_).AddressFamily -eq [System.Net.Sockets.AddressFamily]::InterNetwork })]
    [string]$LanAddress,
    [ValidateRange(1, 65535)][int]$EntryPort = 3000,
    [switch]$OwnerApproved
)

$ErrorActionPreference = 'Stop'
$ruleName = 'Local3D LAN Web Entry'

if (-not $OwnerApproved) {
    throw 'Owner approval is required. Re-run with -OwnerApproved only for a private LAN address.'
}

$bytes = [System.Net.IPAddress]::Parse($LanAddress).GetAddressBytes()
$isPrivate = $bytes[0] -eq 10 -or
    ($bytes[0] -eq 172 -and $bytes[1] -ge 16 -and $bytes[1] -le 31) -or
    ($bytes[0] -eq 192 -and $bytes[1] -eq 168)
if (-not $isPrivate) {
    throw "LAN entry address must be RFC1918 private IPv4; received $LanAddress."
}

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Administrator rights are required to configure the LAN boundary.'
}
if ($null -eq (Get-NetIPAddress -AddressFamily IPv4 -IPAddress $LanAddress -ErrorAction SilentlyContinue)) {
    throw "$LanAddress is not currently assigned to this server."
}

$proxyText = (& netsh interface portproxy show v4tov4) -join "`n"
$escapedAddress = [regex]::Escape($LanAddress)
$exactProxy = $proxyText -match "(?m)^\s*$escapedAddress\s+$EntryPort\s+127\.0\.0\.1\s+3000\s*$"
if (-not $exactProxy) {
    & netsh interface portproxy delete v4tov4 listenaddress=$LanAddress listenport=$EntryPort protocol=tcp | Out-Null
    & netsh interface portproxy add v4tov4 listenaddress=$LanAddress listenport=$EntryPort connectaddress=127.0.0.1 connectport=3000 protocol=tcp | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw 'Failed to create the LAN-to-loopback web proxy.'
    }
}

Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue |
    Remove-NetFirewallRule -ErrorAction Stop
New-NetFirewallRule `
    -DisplayName $ruleName `
    -Description 'Owner-approved Local3D web entry; private LAN clients only.' `
    -Direction Inbound `
    -Action Allow `
    -Enabled True `
    -Profile Any `
    -Protocol TCP `
    -LocalAddress $LanAddress `
    -LocalPort $EntryPort `
    -RemoteAddress LocalSubnet | Out-Null

Write-Output "Configured approved LAN entry: http://${LanAddress}:$EntryPort/"
Write-Output 'Internal ports 8000 and 8188 were not exposed.'
