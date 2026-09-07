[CmdletBinding()]
param(
    [string]$StatePath = (Join-Path $env:ProgramData 'Local3D\quick-tunnel.json'),
    [switch]$Elevate
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
$isAdministrator = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if ($Elevate -and -not $isAdministrator) {
    Write-Output 'Requesting Administrator permission to stop the Quick Tunnel...'
    $arguments = @(
        '-NoProfile',
        '-ExecutionPolicy', 'Bypass',
        '-File', "`"$PSCommandPath`"",
        '-StatePath', "`"$StatePath`""
    )
    $elevated = Start-Process -FilePath 'powershell.exe' -ArgumentList $arguments -Verb RunAs -Wait -PassThru
    exit $elevated.ExitCode
}

if (-not (Test-Path -LiteralPath $StatePath)) {
    Write-Output 'PASS: no recorded Quick Tunnel session is running.'
    return
}
$state = Get-Content -LiteralPath $StatePath -Raw | ConvertFrom-Json
$process = Get-Process -Id ([int]$state.pid) -ErrorAction SilentlyContinue
if ($null -ne $process) {
    if ($process.ProcessName -ne 'cloudflared') {
        throw "Refusing to stop PID $($process.Id): the recorded PID now belongs to $($process.ProcessName), not cloudflared."
    }
    try {
        Stop-Process -Id $process.Id -Force -ErrorAction Stop
        Wait-Process -Id $process.Id -Timeout 10 -ErrorAction SilentlyContinue
    } catch {
        if (-not $isAdministrator -and $_.Exception.Message -match 'Access is denied') {
            throw "Access is denied because cloudflared was started by an elevated session. Re-run this script with -Elevate to approve the Administrator prompt."
        }
        throw
    }
    Write-Output 'PASS: temporary Quick Tunnel process stopped.'
} else {
    Write-Output 'PASS: recorded Quick Tunnel process was already absent.'
}
Remove-Item -LiteralPath $StatePath -Force -ErrorAction SilentlyContinue
