# Feature 004 — Single-Node Windows AI Server Runbook

This is the active operator procedure for the approved architecture. The
Notebook/PC assigned `161.200.90.4` is the only server and runs ComfyUI,
FastAPI, the frontend, Caddy, and the RTX 5070 workload.

## Non-negotiable boundary

```text
Public user -> temporary HTTPS URL -> Cloudflare Quick Tunnel
-> cloudflared (outbound) -> Caddy 127.0.0.1:8080
-> Web 127.0.0.1:3000 / API 127.0.0.1:8000
-> ComfyUI 127.0.0.1:8188 -> RTX 5070
```

Do not add an edge server, WireGuard, port forwarding, public DNS, a custom
hostname, or an inbound firewall rule. The assigned IP identifies the
machine; it is not the application URL. FastAPI and ComfyUI must never be
reachable directly from the Internet.

## Start and verify locally

From the repository root, in an elevated PowerShell only when service control
is required:

```powershell
Get-Service Local3D-ComfyUI,Local3D-API,Local3D-Web,Local3D-Caddy
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/windows/health_chain.ps1 -Json
```

The required order is ComfyUI → API → Web → Caddy. The expected application
listeners are exactly `127.0.0.1:8188`, `127.0.0.1:8000`,
`127.0.0.1:3000`, and `127.0.0.1:8080`. Any `0.0.0.0` or assigned-address
listener is a stop condition.

Validate Caddy with loopback origins:

```powershell
$env:API_UPSTREAM='http://127.0.0.1:8000'
$env:WEB_UPSTREAM='http://127.0.0.1:3000'
$env:CADDY_MAINTENANCE_ROOT=(Resolve-Path deploy/caddy/maintenance).Path
$env:CADDY_LOG_PATH=(Join-Path (Resolve-Path evidence/feature-004).Path 'caddy-access.log')
& .\tmp\caddy-validation\caddy.exe validate --config .\deploy\caddy\Caddyfile --adapter caddyfile
```

Check `/`, `/api/v1/health/live`, `/api/v1/health/ready`, and
`/api/v1/health/engine` through `http://127.0.0.1:8080` before any public test.

## Quick Tunnel test

Only after the local chain is healthy, run the operator-owned session:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/windows/start_quick_tunnel.ps1 -CloudflaredPath cloudflared
```

Use only the random `https://<random>.trycloudflare.com` address printed in
that session. It is public, temporary, and not authentication. Do not save it
in Git, create DNS, configure a named tunnel, or point the tunnel anywhere
other than `http://127.0.0.1:8080`. Stop with Ctrl+C.

## Diagnosis and recovery

Run `health_chain.ps1 -Json` and repair only the failed layer. Preserve the
last durable job state; never resubmit uncertain ComfyUI work automatically.
An API or ComfyUI restart must leave queued jobs queued and uncertain
reserved/running jobs failed safely with a recovery reason. Generated output
must be revalidated before it is reported as completed.

Logs may contain request IDs, safe job IDs, transitions, durations, and failure
categories. They must not contain tokens, authorization headers, filenames,
private paths, engine IDs, generated URLs, or user content.

## Shutdown and reboot checklist

Stop the Quick Tunnel first, then Caddy, Web, API, and ComfyUI. A reboot is an
operator action: after startup verify all four services, loopback listeners,
GPU readiness, storage/workflow readiness, durable job recovery, and the
listener boundary before starting a new Quick Tunnel. Do not claim reboot
acceptance without a real reboot and recorded evidence.

## Authorization gate

A stable custom hostname can be documented only after explicit authorization
to use its parent domain. Domain purchase, DNS changes, production hostname,
or a second server are outside this runbook.
