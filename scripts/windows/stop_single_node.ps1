[CmdletBinding()]
param([int]$TimeoutSeconds = 60)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$order = @('Local3D-Caddy', 'Local3D-Web', 'Local3D-API', 'Local3D-ComfyUI')
foreach ($name in $order) {
    $service = Get-Service -Name $name -ErrorAction SilentlyContinue
    if ($null -eq $service -or $service.Status -eq 'Stopped') { continue }
    Stop-Service -Name $name -Force
    $service.WaitForStatus('Stopped', [TimeSpan]::FromSeconds($TimeoutSeconds))
}
Write-Output 'PASS: Local3D-Caddy -> Local3D-Web -> Local3D-API -> Local3D-ComfyUI stopped.'
