[CmdletBinding()]
param([string]$ProjectRoot = '', [string]$NginxPath = '')
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$root = if ($ProjectRoot) { (Resolve-Path $ProjectRoot).Path } else { (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path }
if (-not $NginxPath) { $NginxPath = Join-Path $root 'deploy\windows\services\nginx.exe' }
if (-not (Test-Path $NginxPath)) { throw "Nginx executable not found: $NginxPath" }
$config = Join-Path $root 'deploy\nginx\nginx.conf'
& $NginxPath -t -p (Join-Path $root 'deploy\nginx') -c $config
if ($LASTEXITCODE -ne 0) { throw 'Nginx configuration validation failed.' }
$caddy = Get-Service -Name Local3D-Caddy -ErrorAction SilentlyContinue
if ($caddy -and $caddy.Status -eq 'Running') { throw 'Local3D-Caddy owns the proxy lifecycle; stop or disable it before Nginx.' }
$existing = Get-NetTCPConnection -State Listen -LocalPort 8080 -ErrorAction SilentlyContinue
if ($existing -and @($existing | Where-Object { $_.LocalAddress -notin @('127.0.0.1','::1') }).Count) { throw 'Refusing to start: port 8080 has a non-loopback listener.' }
$service = Get-Service -Name Local3D-Nginx -ErrorAction Stop
if ($service.Status -ne 'Running') { Start-Service Local3D-Nginx }
$deadline = [DateTime]::UtcNow.AddSeconds(30)
do {
  try { $response = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8080/api/v1/health/live' -Headers @{ Host = 'mango74-api.mangosgo.com' } -TimeoutSec 3; if ($response.StatusCode -eq 200) { Write-Output 'PASS: Local3D-Nginx is running and loopback health is ready.'; exit 0 } } catch {}
  Start-Sleep -Seconds 1
} while ([DateTime]::UtcNow -lt $deadline)
throw 'Nginx did not become healthy within 30 seconds.'
