[CmdletBinding()]
param(
    [ValidateRange(1, 65535)][int]$Port = 3000
)

# Starts Next.js on loopback, unconditionally. Public access is provided only
# by cloudflared -> Caddy; this process never waits for or binds a LAN/tunnel
# interface.

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Write-Output "Starting Next.js on 127.0.0.1:${Port} (no private-binding wait)..."

$nodeExe = 'C:\Program Files\nodejs\node.exe'
$webDir = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..\apps\web')).Path
Set-Location -LiteralPath $webDir

& $nodeExe 'node_modules\next\dist\bin\next' start --hostname 127.0.0.1 --port $Port
exit $LASTEXITCODE
