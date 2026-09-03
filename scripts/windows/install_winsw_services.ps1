[CmdletBinding()]
param(
    [string]$ProjectRoot = '',
    [Parameter(Mandatory = $true)][string]$WinSWPath,
    [Parameter(Mandatory = $true)][ValidatePattern('^[0-9a-fA-F]{64}$')][string]$ExpectedWinSWSha256,
    [switch]$StartServices
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
    $ProjectRoot = (Resolve-Path (Join-Path $scriptRoot '..\..')).Path
}
$ProjectRoot = (Resolve-Path $ProjectRoot).Path
$serviceRoot = Join-Path $ProjectRoot 'deploy\windows\services'
$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'An elevated administrator session is required to install Windows services.'
}

function Grant-LocalServiceAccess {
    param(
        [Parameter(Mandatory = $true)][string]$LiteralPath,
        [Parameter(Mandatory = $true)][ValidateSet('RX', 'M')][string]$Permission
    )

    if (-not (Test-Path -LiteralPath $LiteralPath)) {
        throw "Cannot grant LocalService access because the path does not exist: $LiteralPath"
    }
    & icacls.exe $LiteralPath /grant "*S-1-5-19:(OI)(CI)$Permission" /Q | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to grant LocalService $Permission access to $LiteralPath."
    }
}

function Grant-LocalServiceTraverseAccess {
    param([Parameter(Mandatory = $true)][string]$LiteralPath)

    if (-not (Test-Path -LiteralPath $LiteralPath)) {
        throw "Cannot grant LocalService traverse access because the path does not exist: $LiteralPath"
    }
    & icacls.exe $LiteralPath /grant '*S-1-5-19:(S,RA,X)' /Q | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to grant LocalService traverse/read-attributes access to $LiteralPath."
    }
}

# The restricted service account must be able to traverse source/runtime files,
# while write access remains limited to runtime state and log directories.
$storageRoot = Join-Path $ProjectRoot 'storage'
$comfyRoot = 'C:\Users\MetaHosP\ComfyUI'
$mutablePaths = @(
    $serviceRoot,
    $storageRoot,
    (Join-Path $comfyRoot 'input'),
    (Join-Path $comfyRoot 'output'),
    (Join-Path $comfyRoot 'temp'),
    (Join-Path $comfyRoot 'user'),
    (Join-Path $comfyRoot 'user\service-cache')
)
foreach ($path in $mutablePaths) {
    if (-not (Test-Path -LiteralPath $path)) {
        New-Item -ItemType Directory -Path $path -Force | Out-Null
    }
}

Grant-LocalServiceAccess -LiteralPath $ProjectRoot -Permission RX
Grant-LocalServiceAccess -LiteralPath $comfyRoot -Permission RX
Grant-LocalServiceTraverseAccess -LiteralPath 'C:\Users\MetaHosP'
Grant-LocalServiceTraverseAccess -LiteralPath 'C:\Users\MetaHosP\Desktop'
foreach ($path in $mutablePaths) {
    Grant-LocalServiceAccess -LiteralPath $path -Permission M
}

# A Windows venv launcher delegates to its base Python installation. Grant only
# read/execute on each base runtime discovered from pyvenv.cfg.
$venvConfigs = @(
    (Join-Path $ProjectRoot 'apps\api\.venv\pyvenv.cfg'),
    (Join-Path $comfyRoot 'venv\pyvenv.cfg')
)
foreach ($venvConfig in $venvConfigs) {
    if (-not (Test-Path -LiteralPath $venvConfig)) { continue }
    $homeLine = Get-Content -LiteralPath $venvConfig | Where-Object { $_ -match '^\s*home\s*=' } | Select-Object -First 1
    if ($homeLine) {
        $pythonHome = ($homeLine -split '=', 2)[1].Trim()
        Grant-LocalServiceAccess -LiteralPath $pythonHome -Permission RX
    }
}

$source = (Resolve-Path $WinSWPath).Path
$actualHash = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
if ($actualHash -ne $ExpectedWinSWSha256.ToUpperInvariant()) {
    throw 'The supplied WinSW binary hash does not match the operator-provided expected hash.'
}

$services = @(
    [PSCustomObject]@{ Id = 'Local3D-ComfyUI'; Definition = 'comfyui.xml' }
    [PSCustomObject]@{ Id = 'Local3D-API'; Definition = 'api.xml' }
    [PSCustomObject]@{ Id = 'Local3D-Web'; Definition = 'web.xml' }
)

# Service-account and dependency changes are install-time settings in WinSW v2.
# Remove an earlier installation in reverse dependency order before reinstalling.
foreach ($service in $services[($services.Count - 1)..0]) {
    $existing = Get-Service -Name $service.Id -ErrorAction SilentlyContinue
    if ($null -eq $existing) { continue }

    if ($existing.Status -ne 'Stopped') {
        Stop-Service -Name $service.Id -Force
        $existing.WaitForStatus('Stopped', [TimeSpan]::FromSeconds(60))
    }
    $existingWrapper = Join-Path $serviceRoot "$($service.Id).exe"
    if (-not (Test-Path -LiteralPath $existingWrapper)) {
        throw "Cannot safely reinstall $($service.Id): existing WinSW wrapper is missing."
    }
    & $existingWrapper uninstall | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "WinSW uninstall failed for $($service.Id)." }

    $deadline = [DateTime]::UtcNow.AddSeconds(30)
    while ((Get-Service -Name $service.Id -ErrorAction SilentlyContinue) -and [DateTime]::UtcNow -lt $deadline) {
        Start-Sleep -Milliseconds 250
    }
    if (Get-Service -Name $service.Id -ErrorAction SilentlyContinue) {
        throw "Service $($service.Id) still exists after WinSW uninstall."
    }
}

foreach ($service in $services) {
    $definitionPath = Join-Path $serviceRoot $service.Definition
    [xml]$definition = Get-Content -Raw -LiteralPath $definitionPath
    if ([string]$definition.service.id -ne $service.Id) {
        throw "Service definition ID mismatch for $($service.Definition)."
    }
    $wrapperPath = Join-Path $serviceRoot "$($service.Id).exe"
    Copy-Item -LiteralPath $source -Destination $wrapperPath -Force
    Copy-Item -LiteralPath $definitionPath -Destination (Join-Path $serviceRoot "$($service.Id).xml") -Force
    & $wrapperPath install | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "WinSW install failed for $($service.Id)." }
}

if ($StartServices) {
    foreach ($service in $services) {
        Start-Service -Name $service.Id
        $state = (Get-Service -Name $service.Id).Status
        if ($state -ne 'Running') { throw "Service $($service.Id) did not reach Running state." }
    }
}

Write-Output 'PASS: WinSW wrappers installed from the operator-supplied hash-verified binary.'
if ($StartServices) {
    Write-Output 'PASS: services started in dependency order; run verify_services.ps1 -RunGeneration next.'
} else {
    Write-Output 'NEXT: run verify_services.ps1 -RunGeneration after starting the services in dependency order.'
}
