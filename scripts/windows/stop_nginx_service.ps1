[CmdletBinding()]
param([int]$TimeoutSeconds = 30)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$service = Get-Service -Name Local3D-Nginx -ErrorAction Stop
if ($service.Status -ne 'Stopped') { Stop-Service -Name Local3D-Nginx }
$deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
do { $state = (Get-Service -Name Local3D-Nginx).Status; if ($state -eq 'Stopped') { break }; Start-Sleep -Milliseconds 500 } while ([DateTime]::UtcNow -lt $deadline)
if ((Get-Service -Name Local3D-Nginx).Status -ne 'Stopped') { throw 'Local3D-Nginx did not stop within the bounded timeout.' }
$listeners = @(Get-NetTCPConnection -State Listen -LocalPort 8080 -ErrorAction SilentlyContinue)
if ($listeners.Count) { throw 'Port 8080 remains occupied after stopping Local3D-Nginx.' }
Write-Output 'PASS: Local3D-Nginx stopped and port 8080 was released.'
