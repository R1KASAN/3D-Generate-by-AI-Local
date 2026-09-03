[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$LanAddress,
    [ValidateRange(1, 65535)][int]$EntryPort = 3000
)

$ErrorActionPreference = 'Stop'
$ruleName = 'Local3D LAN Web Entry'
$failures = [System.Collections.Generic.List[string]]::new()

$listeners = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue
foreach ($port in 8000, 8188) {
    $unsafe = @($listeners | Where-Object {
        $_.LocalPort -eq $port -and $_.LocalAddress -notin @('127.0.0.1', '::1')
    })
    if ($unsafe.Count -gt 0) {
        $failures.Add("Port $port has a non-loopback listener.")
    }
}

$proxyText = (& netsh interface portproxy show v4tov4) -join "`n"
$escapedAddress = [regex]::Escape($LanAddress)
if ($proxyText -notmatch "(?m)^\s*$escapedAddress\s+$EntryPort\s+127\.0\.0\.1\s+3000\s*$") {
    $failures.Add('The approved LAN-to-loopback web proxy is absent or differs from the expected target.')
}

$rules = @(Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue)
if ($rules.Count -ne 1) {
    $failures.Add('Exactly one approved LAN web firewall rule is required.')
} else {
    $rule = $rules[0]
    $portFilter = $rule | Get-NetFirewallPortFilter
    $addressFilter = $rule | Get-NetFirewallAddressFilter
    if ($rule.Enabled -ne 'True' -or $rule.Direction -ne 'Inbound' -or $rule.Action -ne 'Allow') {
        $failures.Add('The LAN web firewall rule is not an enabled inbound allow rule.')
    }
    if ($portFilter.Protocol -ne 'TCP' -or [string]$portFilter.LocalPort -ne [string]$EntryPort) {
        $failures.Add('The LAN web firewall rule permits an unexpected protocol or port.')
    }
    if ([string]$addressFilter.LocalAddress -ne $LanAddress -or [string]$addressFilter.RemoteAddress -ne 'LocalSubnet') {
        $failures.Add('The LAN web firewall rule is not limited to the selected server address and local subnet.')
    }
}

try {
    $response = Invoke-WebRequest -UseBasicParsing -Uri "http://${LanAddress}:$EntryPort/" -TimeoutSec 10
    if ($response.StatusCode -lt 200 -or $response.StatusCode -ge 300) {
        $failures.Add("The approved LAN entry returned HTTP $($response.StatusCode).")
    }
} catch {
    $failures.Add("The approved LAN entry was not reachable locally: $($_.Exception.GetType().Name).")
}

if ($failures.Count -gt 0) {
    $failures | ForEach-Object { Write-Error $_ }
    exit 1
}

Write-Output "PASS: approved LAN entry http://${LanAddress}:$EntryPort/ targets loopback web only."
Write-Output 'PASS: ports 8000 and 8188 have no non-loopback listeners.'
