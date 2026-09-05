[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$PublicAddress,
    [Parameter(Mandatory = $true)][string]$ManagementSourceCidr,
    [Parameter(Mandatory = $true)][ValidateRange(1, 65535)][int]$ManagementPort,
    [Parameter(Mandatory = $true)][string[]]$CloudflareRange,
    [ValidateRange(1, 65535)][int]$WireGuardPort = 51820,
    [string]$Evidence = 'evidence/public-deployment/firewall.md'
)

# Read-only verifier for the origin boundary. It never creates, removes, or
# edits firewall rules. Evidence masks all address values before writing.

$ErrorActionPreference = 'Stop'
$approvedPublicAddress = '161.200.90.4'
if ($PublicAddress -ne $approvedPublicAddress) { throw "PublicAddress must be exactly $approvedPublicAddress." }

$failures = [System.Collections.Generic.List[string]]::new()
$checks = [System.Collections.Generic.List[pscustomobject]]::new()
function Add-Check($name, $observed, $expected, $pass) {
    $checks.Add([pscustomobject]@{ Name = $name; Observed = $observed; Expected = $expected; Pass = [bool]$pass })
    if (-not $pass) { $script:failures.Add("${name}: $observed") }
}
function Mask-Address($value) {
    if ($value -is [array]) { return (($value | ForEach-Object { Mask-Address $_ }) -join ',') }
    return ([string]$value -replace '(\d+\.\d+\.\d+)\.\d+', '$1.x')
}

$providerRanges = @($CloudflareRange | ForEach-Object { $_.Trim() } | Where-Object { $_ } | Sort-Object -Unique)
Add-Check 'provider-ranges-supplied' (Mask-Address $providerRanges) 'current non-empty Cloudflare CIDR list' ($providerRanges.Count -gt 0 -and 'Any' -notin $providerRanges)

$httpsRules = @(Get-NetFirewallRule -DisplayName 'Local3D Edge HTTPS' -ErrorAction SilentlyContinue)
if ($httpsRules.Count -ne 1) {
    Add-Check 'https-rule-count' "$($httpsRules.Count)" '1' $false
} else {
    $https = $httpsRules[0]
    $httpsPort = $https | Get-NetFirewallPortFilter
    $httpsAddress = $https | Get-NetFirewallAddressFilter
    $actualRanges = @($httpsAddress.RemoteAddress | ForEach-Object { [string]$_ } | Sort-Object -Unique)
    $scopeOk = $https.Enabled -eq 'True' -and $https.Direction -eq 'Inbound' -and $https.Action -eq 'Allow' -and $httpsPort.Protocol -eq 'TCP' -and [string]$httpsPort.LocalPort -eq '443' -and [string]$httpsAddress.LocalAddress -eq $PublicAddress -and 'Any' -notin $actualRanges -and (@(Compare-Object $providerRanges $actualRanges).Count -eq 0)
    Add-Check 'https-rule-scope' "enabled=$($https.Enabled) remote=$(Mask-Address $actualRanges)" '443/tcp from current Cloudflare ranges only' $scopeOk
}

$httpAllow = @(Get-NetFirewallRule -Direction Inbound -Action Allow -ErrorAction SilentlyContinue | Where-Object { $f = $_ | Get-NetFirewallPortFilter; [string]$f.LocalPort -match '(^|,)80($|,)' })
$httpBlock = @(Get-NetFirewallRule -DisplayName 'Local3D Edge Explicit Block 80' -ErrorAction SilentlyContinue)
Add-Check 'port-80-no-allow' "$($httpAllow.Count) allow rule(s)" '0 allow rules' ($httpAllow.Count -eq 0)
Add-Check 'port-80-explicit-block' "$($httpBlock.Count) block rule(s)" 'at least 1 block rule' ($httpBlock.Count -ge 1)

$wgRules = @(Get-NetFirewallRule -DisplayName 'Local3D Edge WireGuard' -ErrorAction SilentlyContinue)
if ($wgRules.Count -ne 1) {
    Add-Check 'wireguard-rule-count' "$($wgRules.Count)" '1' $false
} else {
    $wg = $wgRules[0]
    $wgPort = $wg | Get-NetFirewallPortFilter
    $wgAddress = $wg | Get-NetFirewallAddressFilter
    Add-Check 'wireguard-rule' "enabled=$($wg.Enabled) proto=$($wgPort.Protocol) port=$($wgPort.LocalPort) remote=$($wgAddress.RemoteAddress)" "51820/udp from Any" ($wg.Enabled -eq 'True' -and $wg.Direction -eq 'Inbound' -and $wg.Action -eq 'Allow' -and $wgPort.Protocol -eq 'UDP' -and [string]$wgPort.LocalPort -eq [string]$WireGuardPort -and [string]$wgAddress.RemoteAddress -eq 'Any')
}

$mgmtRules = @(Get-NetFirewallRule -DisplayName 'Local3D Edge Management' -ErrorAction SilentlyContinue)
if ($mgmtRules.Count -ne 1) {
    Add-Check 'management-rule-count' "$($mgmtRules.Count)" '1' $false
} else {
    $mgmt = $mgmtRules[0]
    $mgmtPort = $mgmt | Get-NetFirewallPortFilter
    $mgmtAddress = $mgmt | Get-NetFirewallAddressFilter
    Add-Check 'management-rule-scope' "port=$($mgmtPort.LocalPort) remote=$(Mask-Address $mgmtAddress.RemoteAddress)" "TCP $ManagementPort from approved source only" ($mgmt.Enabled -eq 'True' -and $mgmt.Direction -eq 'Inbound' -and $mgmt.Action -eq 'Allow' -and [string]$mgmtPort.LocalPort -eq [string]$ManagementPort -and [string]$mgmtAddress.RemoteAddress -eq $ManagementSourceCidr -and [string]$mgmtAddress.RemoteAddress -ne 'Any')
}

foreach ($port in 3000, 8000, 8188, 3389, 2019) {
    $rules = @(Get-NetFirewallRule -DisplayName "Local3D Edge Explicit Block $port" -ErrorAction SilentlyContinue)
    Add-Check "explicit-block-$port" "$($rules.Count) rule(s)" 'at least 1 block rule' ($rules.Count -ge 1)
}
$profiles = @(Get-NetFirewallProfile -All)
Add-Check 'default-deny-profiles' "$(($profiles | Where-Object { $_.Enabled -ne $true -or $_.DefaultInboundAction -ne 'Block' }).Count) non-compliant profile(s)" 'all profiles enabled with inbound Block' (@($profiles | Where-Object { $_.Enabled -ne $true -or $_.DefaultInboundAction -ne 'Block' }).Count -eq 0)

$evidenceDir = Split-Path -Parent $Evidence
if ($evidenceDir -and -not (Test-Path -LiteralPath $evidenceDir)) { New-Item -ItemType Directory -Path $evidenceDir -Force | Out-Null }
$lines = [System.Collections.Generic.List[string]]::new()
$lines.Add('# Public Edge Firewall Evidence')
$lines.Add('')
$lines.Add("- Date/time (UTC): $([DateTime]::UtcNow.ToString('o'))")
$lines.Add("- Origin address (masked): $(Mask-Address $PublicAddress)")
$lines.Add('- Credentials, tokens, private keys, and unmasked addresses are omitted.')
$lines.Add('')
$lines.Add('| Check | Observed | Expected | Verdict |')
$lines.Add('|---|---|---|---|')
foreach ($check in $checks) {
    $lines.Add("| $($check.Name) | $(Mask-Address $check.Observed) | $(Mask-Address $check.Expected) | $(if ($check.Pass) { '**PASS**' } else { '**FAIL**' }) |")
}
$overall = if ($failures.Count -eq 0) { '**PASS**' } else { '**FAIL**' }
$lines.Add('')
$lines.Add("- Overall verdict: $overall")
Set-Content -LiteralPath $Evidence -Value ($lines -join "`n") -Encoding UTF8
if ($failures.Count -gt 0) { $failures | ForEach-Object { Write-Error $_ }; exit 1 }
Write-Output "PASS: public edge boundary verified. Evidence written to $Evidence."
