# Feature 005 health-chain snapshot

Command executed from the repository root:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows\health_chain.ps1 -Feature005 -Json
```

Result: exit code `0`.

Passing checks:

- Nginx: `loopback Nginx :8080`
- FastAPI: healthy
- Storage: healthy
- Workflow manifest: healthy
- ComfyUI loopback: healthy
- GPU driver probe: healthy
- Listener boundary: `application ports loopback-only`
- Process boundary: `Nginx service running and Caddy not running; definition=nginx.xml`

Not yet available (correctly reported as false, not converted to PASS):

- Named Tunnel: `named Tunnel service is checked by verify_named_tunnel.ps1`
- Stable public API: `stable API URL not supplied`

The local Nginx service is installed and running; named Cloudflare Tunnel,
stable API hostname, and production external routing still require the
authorized administrator gates in tasks T042/T082 and subsequent tasks.

The same command was rerun after the Firebase preview change. The result was
unchanged: all local Nginx/API/storage/workflow/ComfyUI/GPU/listener/process
checks remained healthy, while Named Tunnel and Stable public API remained
false because those administrator-controlled dependencies are still absent.

## Post-connector snapshot — 2026-09-09T20:42:34Z

Commands:

```powershell
.\scripts\windows\verify_named_tunnel.ps1 `
  -ApiHealthUrl https://mango74-api.mangosgo.com/api/v1/health/live

.\scripts\windows\health_chain.ps1 -Feature005 `
  -StableApiUrl https://mango74-api.mangosgo.com/api/v1 -Json
```

Observed:

- `cloudflared` service: running and automatic; Cloudflare connector status
  `Healthy`.
- Nginx, FastAPI, storage, workflow, ComfyUI, GPU, listener boundary, and
  process boundary: healthy.
- Named-Tunnel verifier: `ServiceRunning=true`, but public status/CORS absent;
  exit code `1`.
- Stable public API: false because the required hostname does not yet resolve.
- The health-chain JSON command exited `0` by design while retaining false
  component values; it is **not** treated as an overall PASS.

Result: **BLOCKED — T083 remains open until the `mangosgo.com` zone
administrator publishes the Tunnel DNS record and both HTTPS health and exact
CORS verification pass.**
