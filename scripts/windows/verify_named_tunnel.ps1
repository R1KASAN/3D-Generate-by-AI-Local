[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][ValidatePattern('^https://[^/]+/api/v1/health/live$')][string]$ApiHealthUrl,
    [string]$ServiceName = 'cloudflared'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$uri = [Uri]$ApiHealthUrl
if ($uri.Host -match '(?i)(trycloudflare\.com|localhost|127\.0\.0\.1)$' -or $uri.Host -match '^\d') {
    throw 'The named-Tunnel verifier refuses temporary, local, or raw IP URLs.'
}
$service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
$serviceHealthy = $null -ne $service -and $service.Status -eq 'Running'
$httpHealthy = $false
$statusCode = $null
$corsOrigin = $null
try {
    $response = Invoke-WebRequest -UseBasicParsing -Uri $ApiHealthUrl -Headers @{ Origin = 'https://www.mangosgo.com' } -TimeoutSec 10 -ErrorAction Stop
    $statusCode = [int]$response.StatusCode
    $corsOrigin = [string]$response.Headers['Access-Control-Allow-Origin']
    $httpHealthy = $statusCode -eq 200
} catch {
    $httpHealthy = $false
}
$result = [pscustomobject]@{
    Service = $ServiceName
    ServiceRunning = $serviceHealthy
    StableApiHttps = $uri.Scheme -eq 'https'
    Host = $uri.Host
    StatusCode = $statusCode
    CorsAllowOrigin = $corsOrigin
    Healthy = $serviceHealthy -and $httpHealthy -and $corsOrigin -eq 'https://www.mangosgo.com'
}
$result | ConvertTo-Json -Depth 3
if (-not $result.Healthy) { exit 1 }
