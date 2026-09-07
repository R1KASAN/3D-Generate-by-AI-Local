[CmdletBinding()]
param([int]$TimeoutSeconds = 60)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$order = @('Local3D-ComfyUI', 'Local3D-API', 'Local3D-Web', 'Local3D-Caddy')
$started = [System.Collections.Generic.List[string]]::new()

try {
    foreach ($name in $order) {
        $service = Get-Service -Name $name -ErrorAction Stop
        if ($service.Status -eq 'Running') { continue }
        Start-Service -Name $name
        $service.WaitForStatus('Running', [TimeSpan]::FromSeconds($TimeoutSeconds))
        $started.Add($name)
    }
    Write-Output 'PASS: Local3D-ComfyUI -> Local3D-API -> Local3D-Web -> Local3D-Caddy are running.'
} catch {
    $rollback = $started.ToArray()
    [Array]::Reverse($rollback)
    foreach ($name in $rollback) {
        try { Stop-Service -Name $name -Force -ErrorAction Stop } catch { Write-Warning "Rollback could not stop ${name}: $($_.Exception.Message)" }
    }
    throw
}
