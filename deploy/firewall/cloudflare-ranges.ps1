[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$PublicAddress,
    [Parameter(Mandatory = $true)][string]$CloudflareHttpsRuleName,
    [Parameter(Mandatory = $true)][switch]$OwnerApproved,
    [string[]]$RangeUri = @(
        'https://www.cloudflare.com/ips-v4',
        'https://www.cloudflare.com/ips-v6'
    )
)

# Refresh only the existing 443 rule from Cloudflare's published ranges.
# Fetching and validation happen before any firewall mutation. A failed fetch,
# empty response, invalid CIDR, missing rule, or unexpected rule shape exits
# non-zero and leaves the current rule untouched. There is no Any fallback.

$ErrorActionPreference = 'Stop'

if (-not $OwnerApproved) { throw 'Owner approval is required.' }
$approvedPublicAddress = '161.200.90.4'
if ($PublicAddress -ne $approvedPublicAddress) {
    throw "PublicAddress must be exactly $approvedPublicAddress. Refusing any other address."
}

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Administrator rights are required to refresh the HTTPS rule.'
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

# Do not inspect or change firewall state until every remote response is valid.
$ranges = [System.Collections.Generic.List[string]]::new()
foreach ($uri in $RangeUri) {
    try {
        $response = Invoke-WebRequest -Uri $uri -UseBasicParsing -TimeoutSec 20
        foreach ($line in ($response.Content -split "`r?`n")) {
            $range = $line.Trim()
            if ($range) { $ranges.Add($range) }
        }
    } catch {
        throw "Unable to retrieve Cloudflare ranges from $uri. Existing firewall rule was not changed."
    }
}

$uniqueRanges = @($ranges | Sort-Object -Unique)
if ($uniqueRanges.Count -eq 0) {
    throw 'Cloudflare returned no ranges. Existing firewall rule was not changed.'
}
$invalidRanges = @($uniqueRanges | Where-Object { -not (Test-Cidr $_) })
if ($invalidRanges.Count -gt 0) {
    throw "Cloudflare returned invalid CIDR(s): $($invalidRanges -join ', '). Existing firewall rule was not changed."
}

$rules = @(Get-NetFirewallRule -DisplayName $CloudflareHttpsRuleName -ErrorAction SilentlyContinue)
if ($rules.Count -ne 1) {
    throw "Expected exactly one existing HTTPS firewall rule named '$CloudflareHttpsRuleName'. Existing rules were not changed."
}
$rule = $rules[0]
$portFilter = $rule | Get-NetFirewallPortFilter
$addressFilter = $rule | Get-NetFirewallAddressFilter
if ($rule.Direction -ne 'Inbound' -or $rule.Action -ne 'Allow' -or $portFilter.Protocol -ne 'TCP' -or [string]$portFilter.LocalPort -ne '443' -or [string]$addressFilter.LocalAddress -ne $PublicAddress) {
    throw 'Existing HTTPS rule shape is not the expected 443/tcp origin rule. Existing rule was not changed.'
}

$addressFilter | Set-NetFirewallAddressFilter -RemoteAddress $uniqueRanges -ErrorAction Stop
Write-Output "PASS: refreshed $CloudflareHttpsRuleName with $($uniqueRanges.Count) published CIDR(s). No port 80 rule was created."
