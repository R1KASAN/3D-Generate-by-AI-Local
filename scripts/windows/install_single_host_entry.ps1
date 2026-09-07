[CmdletBinding()]
param(
    [switch]$Install,
    [string]$WinSWPath = '',
    [string]$ExpectedWinSWSha256 = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path

if ($Install -and ([string]::IsNullOrWhiteSpace($WinSWPath) -or
        [string]::IsNullOrWhiteSpace($ExpectedWinSWSha256))) {
    throw 'Install requires -WinSWPath and -ExpectedWinSWSha256 from the operator-approved WinSW package.'
}

$caddy = Join-Path $projectRoot 'tmp\caddy-validation\caddy.exe'
$config = Join-Path $projectRoot 'deploy\caddy\Caddyfile'
$maintenance = Join-Path $projectRoot 'deploy\caddy\maintenance'
foreach ($path in @($caddy, $config, $maintenance)) {
    if (-not (Test-Path -LiteralPath $path)) { throw "Missing local prerequisite: $path" }
}

$env:API_UPSTREAM = 'http://127.0.0.1:8000'
$env:WEB_UPSTREAM = 'http://127.0.0.1:3000'
$env:CADDY_MAINTENANCE_ROOT = $maintenance
$env:CADDY_LOG_PATH = Join-Path $projectRoot 'logs\caddy-access.log'
& $caddy validate --config $config --adapter caddyfile
if ($LASTEXITCODE -ne 0) { throw 'Caddy validation failed.' }

if (-not $Install) {
    Write-Output 'PASS: single-node preflight complete; no service or network state changed.'
    Write-Output 'Run this script with -Install from an elevated shell to install only ComfyUI, API, Web, and Caddy.'
    return
}

$installer = Join-Path $PSScriptRoot 'install_winsw_services.ps1'
& $installer -ProjectRoot $projectRoot -WinSWPath $WinSWPath -ExpectedWinSWSha256 $ExpectedWinSWSha256 -StartServices
if ($LASTEXITCODE -ne 0) { throw 'The approved single-node WinSW installer failed.' }
Write-Output 'PASS: only Local3D-ComfyUI, Local3D-API, Local3D-Web, and Local3D-Caddy were installed.'
