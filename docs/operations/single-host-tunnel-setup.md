# Single-host test entry — Feature 004

This guide is authoritative for the temporary test path. One Notebook/PC is
the project server, including the GPU, ComfyUI, FastAPI, frontend, and Caddy.
The assigned `161.200.90.4` address is not a public application endpoint.

```text
Browser -> Cloudflare -> Quick Tunnel -> cloudflared
-> Caddy 127.0.0.1:8080 -> Web 127.0.0.1:3000 / API 127.0.0.1:8000
-> ComfyUI 127.0.0.1:8188 -> RTX 5070
```

## Local gate

```powershell
Get-NetTCPConnection -State Listen |
  Where-Object { $_.LocalPort -in @(3000,8000,8080,8188) } |
  Select-Object LocalAddress,LocalPort
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/windows/health_chain.ps1 -Json
```

Every application listener must be loopback-only. Caddy must be healthy before
the public test. Validate its environment and configuration:

```powershell
$env:API_UPSTREAM='http://127.0.0.1:8000'
$env:WEB_UPSTREAM='http://127.0.0.1:3000'
$env:CADDY_MAINTENANCE_ROOT=(Resolve-Path deploy/caddy/maintenance).Path
$env:CADDY_LOG_PATH=(Join-Path (Resolve-Path evidence/feature-004).Path 'caddy-access.log')
& .\tmp\caddy-validation\caddy.exe validate --config .\deploy\caddy\Caddyfile --adapter caddyfile
Invoke-WebRequest http://127.0.0.1:8080/
Invoke-WebRequest http://127.0.0.1:8080/api/v1/health/live
```

## Temporary Quick Tunnel

Run this only after the local gate passes:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/windows/start_quick_tunnel.ps1 -CloudflaredPath cloudflared
```

The launcher targets exactly `http://127.0.0.1:8080`, refuses conflicting
named-tunnel defaults, and prints a random `trycloudflare.com` URL. Treat that
URL as public and disposable; it is not authentication. Do not write it to the
repository, create DNS, buy a domain, install a named tunnel, or expose a
direct application port. Quick Tunnels are HTTP polling compatible; do not
assume SSE/WebSocket progress is available through this test path.

## Shutdown and future hostname

Stop the Quick Tunnel with Ctrl+C, then stop Caddy and the application services
in reverse dependency order. Preserve SQLite job state and generated assets.
A custom hostname is future work only after explicit parent-domain
authorization; this guide does not authorize DNS or production cutover.
