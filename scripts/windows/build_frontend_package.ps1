[CmdletBinding()]
param(
    [string]$ProjectRoot = (Get-Location).Path,
    [string]$OutputPath = '',
    [string]$PythonPath = 'python',
    [ValidateSet('production','preview','firebase-preview')][string]$DeploymentEnv = 'production'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $OutputPath = Join-Path $ProjectRoot 'artifacts\front-end.zip'
}
$OutputPath = [IO.Path]::GetFullPath($OutputPath)
$webRoot = Join-Path $ProjectRoot 'apps\web'
$outRoot = Join-Path $webRoot 'out'
$validator = Join-Path $ProjectRoot 'scripts\verify\verify_frontend_package.py'
$manifest = Join-Path ([IO.Path]::GetDirectoryName($OutputPath)) 'front-end.manifest.json'
$firebasePreview = $DeploymentEnv -eq 'firebase-preview'
$firebaseMount = Join-Path $outRoot 'mango74'

if (-not $env:MANGO74_STATIC_EXPORT) { $env:MANGO74_STATIC_EXPORT = '1' }
if (-not $env:NEXT_PUBLIC_BASE_PATH) { $env:NEXT_PUBLIC_BASE_PATH = '/mango74' }
if (-not $env:NEXT_PUBLIC_API_BASE_URL) { $env:NEXT_PUBLIC_API_BASE_URL = 'https://www.mangosgo.com/api/v1' }
$env:NEXT_PUBLIC_DEPLOYMENT_ENV = $DeploymentEnv
try {
    Push-Location $webRoot
    & npm run build
    if ($LASTEXITCODE -ne 0) { throw 'Frontend static build failed.' }
    if (-not (Test-Path -LiteralPath $outRoot)) { throw "Static output not found: $outRoot" }

    # Firebase Hosting serves this preview from its site root, while the
    # compiled application intentionally keeps the production /mango74 base
    # path. Stage a second copy below /mango74 so preview asset URLs resolve
    # without changing the production build contract or API configuration.
    if ($firebasePreview) {
        if (Test-Path -LiteralPath $firebaseMount) {
            Remove-Item -LiteralPath $firebaseMount -Recurse -Force
        }
        New-Item -ItemType Directory -Force -Path $firebaseMount | Out-Null
        Get-ChildItem -LiteralPath $outRoot -Force |
            Where-Object { $_.Name -ne 'mango74' } |
            Copy-Item -Destination $firebaseMount -Recurse -Force
        Write-Output 'PASS: Firebase preview staged under /mango74/.'
    }
    New-Item -ItemType Directory -Force -Path ([IO.Path]::GetDirectoryName($OutputPath)) | Out-Null
    if (Test-Path -LiteralPath $OutputPath) { Remove-Item -LiteralPath $OutputPath -Force }
    & $PythonPath $validator --root $outRoot --manifest $manifest --create-archive $OutputPath
    if ($LASTEXITCODE -ne 0) { throw 'Static package validation failed.' }
    & $PythonPath $validator --archive $OutputPath --manifest $manifest
    if ($LASTEXITCODE -ne 0) { throw 'Archive validation failed.' }
    $hash = (Get-FileHash -LiteralPath $OutputPath -Algorithm SHA256).Hash
    Write-Output "PASS: front-end.zip created; SHA256=$hash"
}
finally {
    Pop-Location
    Remove-Item Env:MANGO74_STATIC_EXPORT -ErrorAction SilentlyContinue
    Remove-Item Env:NEXT_PUBLIC_BASE_PATH -ErrorAction SilentlyContinue
    Remove-Item Env:NEXT_PUBLIC_API_BASE_URL -ErrorAction SilentlyContinue
    Remove-Item Env:NEXT_PUBLIC_DEPLOYMENT_ENV -ErrorAction SilentlyContinue
}
