[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateScript({ [System.Net.IPAddress]::Parse($_).AddressFamily -eq [System.Net.Sockets.AddressFamily]::InterNetwork })]
    [string]$EdgePeer,

    [string]$TunnelAddress = '10.10.0.2',
    [ValidateRange(1, 65535)][int]$WebPort = 3000,
    [string]$Evidence = 'evidence/public-deployment/firewall-upstream.md'
)

# Read-only verifier for the laptop-side boundary (T088), mirroring
# scripts/windows/verify_lan_boundary.ps1's shape: collect PASS/FAIL checks,
# write masked evidence, exit 1 on any failure.

$ErrorActionPreference = 'Stop'
$ruleName = 'Local3D Upstream Entry'
$failures = [System.Collections.Generic.List[string]]::new()
$checks = [System.Collections.Generic.List[pscustomobject]]::new()

function Add-Check($name, $observed, $expected, $pass) {
    $checks.Add([pscustomobject]@{ Name = $name; Observed = $observed; Expected = $expected; Pass = $pass })
    if (-not $pass) { $script:failures.Add("$name: $observed") }
}

# Internal ports stay loopback-only.
$listeners = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue
foreach ($port in 8000, 8188) {
    $unsafe = @($listeners | Where-Object { $_.LocalPort -eq $port -and $_.LocalAddress -notin @('127.0.0.1', '::1') })
    Add-Check "internal-port-$port" ($(if ($unsafe.Count -gt 0) { 'non-loopback listener present' } else { 'loopback only' })) 'loopback only' ($unsafe.Count -eq 0)
}

# Web port listens on the tunnel address, not loopback and not a wildcard.
$webListener = @($listeners | Where-Object { $_.LocalPort -eq $WebPort -and $_.LocalAddress -eq $TunnelAddress })
Add-Check "web-port-$WebPort-bind" ($(if ($webListener.Count -gt 0) { "listening on $TunnelAddress" } else { 'not listening on tunnel address' })) "listening on $TunnelAddress only" ($webListener.Count -gt 0)

# No portproxy entries.
$proxyText = ((& netsh interface portproxy show v4tov4) -join "`n").Trim()
$proxyEmpty = $proxyText -match 'Listen on ipv4:\s*Connect to ipv4:\s*Address\s+Port\s+Address\s+Port\s*-+\s+-+\s+-+\s+-+\s*$'
Add-Check 'portproxy-empty' ($(if ($proxyEmpty) { 'empty' } else { 'entries present' })) 'empty' $proxyEmpty

# Firewall rule is exactly the expected scoped allow rule.
$rules = @(Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue)
if ($rules.Count -ne 1) {
    Add-Check 'upstream-rule-count' "$($rules.Count) rules named '$ruleName'" '1' $false
} else {
    $rule = $rules[0]
    $portFilter = $rule | Get-NetFirewallPortFilter
    $addressFilter = $rule | Get-NetFirewallAddressFilter
    $ok = $rule.Enabled -eq 'True' -and $rule.Direction -eq 'Inbound' -and $rule.Action -eq 'Allow' `
        -and $portFilter.Protocol -eq 'TCP' -and [string]$portFilter.LocalPort -eq [string]$WebPort `
        -and [string]$addressFilter.LocalAddress -eq $TunnelAddress -and [string]$addressFilter.RemoteAddress -eq $EdgePeer
    Add-Check 'upstream-rule-scope' "enabled=$($rule.Enabled) dir=$($rule.Direction) action=$($rule.Action) local=$($addressFilter.LocalAddress):$($portFilter.LocalPort) remote=$($addressFilter.RemoteAddress)" "TCP $TunnelAddress`:$WebPort <- $EdgePeer only" $ok
}

# RDP stays disabled.
$rdpKey = 'HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server'
$rdpDenied = (Get-ItemProperty -Path $rdpKey -Name fDenyTSConnections -ErrorAction SilentlyContinue).fDenyTSConnections
Add-Check 'rdp-disabled' "fDenyTSConnections=$rdpDenied" '1' ($rdpDenied -eq 1)

# Default-deny profiles.
$profiles = Get-NetFirewallProfile -All
$profilesOk = -not ($profiles | Where-Object { $_.Enabled -ne $true -or $_.DefaultInboundAction -ne 'Block' })
Add-Check 'default-deny-profiles' ($(if ($profilesOk) { 'all enabled, DefaultInboundAction=Block' } else { 'a profile is not default-deny' })) 'all enabled, DefaultInboundAction=Block' $profilesOk

# --- Write masked evidence ---
$evidenceDir = Split-Path -Parent $Evidence
if ($evidenceDir -and -not (Test-Path -LiteralPath $evidenceDir)) { New-Item -ItemType Directory -Path $evidenceDir -Force | Out-Null }

$maskedTunnel = ($TunnelAddress -replace '\.\d+$', '.x')
$maskedEdge = ($EdgePeer -replace '\.\d+$', '.x')
$lines = [System.Collections.Generic.List[string]]::new()
$lines.Add('# Upstream (laptop-side) Boundary Evidence (T088)')
$lines.Add('')
$lines.Add("- Date/time (UTC): $([DateTime]::UtcNow.ToString('o'))")
$lines.Add("- Tunnel address (masked): $maskedTunnel")
$lines.Add("- Edge peer (masked): $maskedEdge")
$lines.Add('- Credentials, capability tokens, and private keys are omitted.')
$lines.Add('')
$lines.Add('| Check | Observed | Expected | Verdict |')
$lines.Add('|---|---|---|---|')
foreach ($check in $checks) {
    $verdict = if ($check.Pass) { '**PASS**' } else { '**FAIL**' }
    $lines.Add("| $($check.Name) | $($check.Observed) | $($check.Expected) | $verdict |")
}
$overall = if ($failures.Count -eq 0) { '**PASS**' } else { '**FAIL**' }
$lines.Add('')
$lines.Add("- Overall verdict: $overall")
Set-Content -LiteralPath $Evidence -Value ($lines -join "`n") -Encoding UTF8

if ($failures.Count -gt 0) {
    $failures | ForEach-Object { Write-Error $_ }
    exit 1
}

Write-Output "PASS: upstream boundary verified. Evidence written to $Evidence."
