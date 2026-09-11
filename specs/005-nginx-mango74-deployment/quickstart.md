# Quickstart: Validate the Mango74 Production Design

This guide is the post-implementation validation sequence for Feature 005. It
does not grant Cloudflare or NT Server authority, and it must not be used to
paste Tunnel credentials into the repository, shell transcript, or evidence.

Run commands from:

```powershell
Set-Location 'C:\Users\MetaHosP\Desktop\3D-Generate-by-AI-Local'
```

## 1. Prerequisites

- Node.js 24 and npm 11 matching `apps/web/package.json`.
- Python 3.12 and `uv` matching `apps/api/pyproject.toml`.
- The approved ComfyUI/Hunyuan3D runtime and RTX 5070 Notebook.
- A pinned official Nginx Windows archive and operator-approved SHA-256.
- The four backend services configured for loopback only.
- An authorized Cloudflare administrator for the named Tunnel and
  `mango74-api.mangosgo.com`.
- An authorized NT Server administrator for `/mango74/` deployment and
  rollback.
- A genuinely independent network for final external acceptance.

Before changing production, record the NT Server product/version, its exact
deployment and rollback procedure, the current `/mango74` behavior, and a
representative baseline of unrelated `www.mangosgo.com` paths.

## 2. Run repository validation

```powershell
uv run --project apps/api pytest apps/api/tests tests/security -q
uv run --project apps/api ruff check apps/api/src apps/api/tests
uv run --project apps/api mypy apps/api/src/local3d

npm run test --prefix apps/web
npm run typecheck --prefix apps/web
npm run lint --prefix apps/web
npm run test:e2e --prefix apps/web
```

Expected: all tests execute successfully. Browser tests use an isolated mock
API and test ports; they must not submit real RTX work or use operator data.

Validate the design contracts:

```powershell
uv run --project apps/api python -c "import pathlib,yaml; [yaml.safe_load(p.read_text(encoding='utf-8')) for p in pathlib.Path('specs/005-nginx-mango74-deployment/contracts').glob('*.yaml')]; print('PASS: YAML contracts parse')"
```

## 3. Build the production frontend archive

After the planned build/package script is implemented, run:

```powershell
$env:MANGO74_STATIC_EXPORT = '1'
$env:NEXT_PUBLIC_BASE_PATH = '/mango74'
$env:NEXT_PUBLIC_API_BASE_URL = 'https://mango74-api.mangosgo.com/api/v1'

npm run build --prefix apps/web
powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\windows\build_frontend_package.ps1 `
  -ProjectRoot (Get-Location).Path `
  -OutputPath .\artifacts\front-end.zip
```

Expected:

- the archive is named `front-end.zip`;
- it deploys only beneath `/mango74/`;
- every asset reference contains the correct base path;
- browser API references use only
  `https://mango74-api.mangosgo.com/api/v1`;
- the content allowlist and integrity manifest pass;
- scans find no localhost, private/public Notebook address, Quick Tunnel URL,
  credential, Python/runtime file, database, workflow, model, upload, or GLB.

Clear build variables after validation:

```powershell
Remove-Item Env:MANGO74_STATIC_EXPORT -ErrorAction SilentlyContinue
Remove-Item Env:NEXT_PUBLIC_BASE_PATH -ErrorAction SilentlyContinue
Remove-Item Env:NEXT_PUBLIC_API_BASE_URL -ErrorAction SilentlyContinue
```

## 4. Validate backend configuration and CORS locally

Production API configuration must include:

```text
APP_ENV=production
API_HOST=127.0.0.1
API_PORT=8000
COMFYUI_BASE_URL=http://127.0.0.1:8188
CORS_ALLOWED_ORIGINS=https://www.mangosgo.com
CORS_PREVIEW_ORIGIN_ENABLED=false
```

Use an isolated test instance or the implemented contract tests to verify the
exact CORS matrix. A representative allowed preflight is:

```powershell
curl.exe -i -X OPTIONS http://127.0.0.1:8000/api/v1/jobs `
  -H "Origin: https://www.mangosgo.com" `
  -H "Access-Control-Request-Method: POST" `
  -H "Access-Control-Request-Headers: Content-Type,X-Job-Token"
```

Expected: exact `Access-Control-Allow-Origin`, required methods and headers,
`Vary: Origin`, and no credential sharing.

An unauthorized-origin probe must receive no usable allow-origin response:

```powershell
curl.exe -i -X OPTIONS http://127.0.0.1:8000/api/v1/jobs `
  -H "Origin: https://www.mangosgo.com.evil.example" `
  -H "Access-Control-Request-Method: POST" `
  -H "Access-Control-Request-Headers: Content-Type,X-Job-Token"
```

Repeat for HTTP downgrade, unexpected port, bare domain, unapproved subdomain,
`null`, arbitrary origin, and Firebase with its preview permission both off
and on. CORS approval does not replace job-token isolation tests.

## 5. Validate Nginx before service cutover

Stop and disable `Local3D-Caddy` before Nginx can own `127.0.0.1:8080`. Do not
bind Nginx to `0.0.0.0`, a LAN address, or a public address.

With the operator-verified Nginx binary and implemented config:

```powershell
& '<approved-nginx-path>\nginx.exe' -t `
  -p '<approved-nginx-prefix>' `
  -c '<absolute-or-prefix-relative-nginx.conf>'
```

After `Local3D-Nginx` is installed and running:

```powershell
Get-Service Local3D-ComfyUI,Local3D-API,Local3D-Nginx

curl.exe -i http://127.0.0.1:8080/api/v1/health/live `
  -H "Host: mango74-api.mangosgo.com"

curl.exe -i http://127.0.0.1:8080/ `
  -H "Host: mango74-api.mangosgo.com"

curl.exe -i http://127.0.0.1:8080/api/v1/health/live `
  -H "Host: unauthorized.example"
```

Expected: the exact API Host and path reach FastAPI; root and unmatched Host
are rejected; errors contain no upstream address or local path.

Inspect listener boundaries:

```powershell
Get-NetTCPConnection -State Listen |
  Where-Object LocalPort -In 3000,8000,8080,8188 |
  Sort-Object LocalPort |
  Format-Table LocalAddress,LocalPort,OwningProcess

netsh interface portproxy show all
```

Expected: project application listeners are loopback-only and no portproxy
provides an alternate application route.

## 6. Activate the named Tunnel through the authorized administrator

The Cloudflare administrator must create/approve the named Tunnel and map:

```text
mango74-api.mangosgo.com -> http://127.0.0.1:8080
```

The connector token is transferred securely and installed as a Windows
service without being copied into project files or evidence. Do not use the
Quick Tunnel launcher for production and do not record the token-bearing
command.

Safe local checks after installation:

```powershell
Get-Service cloudflared
Get-Process cloudflared -ErrorAction SilentlyContinue
curl.exe -i https://mango74-api.mangosgo.com/api/v1/health/live `
  -H "Origin: https://www.mangosgo.com"
```

Expected: the service is running, HTTPS is valid, the safe API health response
is reachable, and the exact production CORS header is present.

## 7. Deploy the static frontend through the NT Server administrator

Provide only:

- `artifacts/front-end.zip`;
- its SHA-256 and release manifest;
- the [frontend hosting contract](./contracts/frontend-hosting.md);
- the recorded rollback identifier.

The authorized administrator deploys only `/mango74/`. Verify:

```powershell
curl.exe -I 'https://www.mangosgo.com/mango74?probe=1'
curl.exe -I 'https://www.mangosgo.com/mango74/'
```

Expected: one permanent HTTPS redirect preserves `probe=1`, then the static
page loads. Fetch every release-manifest asset and compare representative
unrelated routes to the pre-change baseline.

## 8. Run external browser and real-GPU acceptance

From a genuinely independent network, use only:

```text
Frontend: https://www.mangosgo.com/mango74/
API:      https://mango74-api.mangosgo.com/api/v1
```

Complete one controlled real job:

1. load the NT-hosted page and verify all assets;
2. upload a valid reference image;
3. observe queued, running, and terminal state accurately;
4. refresh and confirm the same authorized job is recovered;
5. complete a separate queued-job refresh/cancellation scenario;
6. preview and download the finalized GLB;
7. confirm preview/download hashes match and GLB magic is `glTF`;
8. confirm all browser API requests use only the stable API origin;
9. confirm no response reveals internal or temporary URLs.

Do not rerun expensive GPU generation when already captured evidence meets the
specific acceptance criterion.

## 9. Verify interruption and recovery

With explicit operator authorization and no unsafe active-job interruption:

1. stop only the named `cloudflared` service;
2. confirm `https://www.mangosgo.com/mango74/` still loads;
3. confirm the frontend reports AI service unavailable, not job missing;
4. confirm no direct Notebook route becomes available;
5. restart `cloudflared`;
6. confirm the same stable API URL and accurate durable job state return.

Run three controlled backend service-restart trials covering ComfyUI, FastAPI,
Nginx, and the Tunnel connector as specified in
[operator-health-and-rollback.md](./contracts/operator-health-and-rollback.md).

## 10. Prove independent rollback

Perform the approved NT frontend rollback and verify its previous state plus
all unrelated-route baselines without touching the Notebook.

Separately perform the approved backend/Tunnel rollback and verify durable job
state without changing the official frontend URL or static files. The
frontend must accurately show backend unavailability while the route is
rolled back.

Record only commands/actions actually performed, UTC timestamps, release
hashes, route outcomes, service states, sanitized job-state counts, elapsed
rollback time, and blockers. Never record credentials, raw job tokens, user
files, generated model bytes, or private configuration.
