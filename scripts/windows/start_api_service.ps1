[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$PythonPath,
    [string]$HostAddress = '127.0.0.1',
    [ValidateRange(1, 65535)][int]$Port = 8000,
    [string]$ComfyUrl = 'http://127.0.0.1:8188',
    [ValidateRange(1, 3600)][int]$MaxWaitSeconds = 600
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$python = (Resolve-Path -LiteralPath $PythonPath).Path
$healthUrl = $ComfyUrl.TrimEnd('/') + '/system_stats'
$deadline = [DateTime]::UtcNow.AddSeconds($MaxWaitSeconds)

while ([DateTime]::UtcNow -lt $deadline) {
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $healthUrl -TimeoutSec 5
        if ($response.StatusCode -eq 200) { break }
    } catch {
        # ComfyUI loads GPU libraries and custom nodes before opening its port.
    }
    Start-Sleep -Seconds 2
}

if ([DateTime]::UtcNow -ge $deadline) {
    throw "ComfyUI did not become healthy within $MaxWaitSeconds seconds."
}

& $python -m uvicorn local3d.main:app --host $HostAddress --port $Port
exit $LASTEXITCODE
