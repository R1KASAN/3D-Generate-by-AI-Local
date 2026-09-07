# US1 local MVP gate

## Automated evidence completed

```text
uv run --project apps/api pytest apps/api/tests -q
136 passed, 4 skipped in 9.89s

npm test --prefix apps/web -- --run
16 passed
npm run typecheck --prefix apps/web
PASS
npm run lint --prefix apps/web
PASS

$env:CADDY_BINARY=(Resolve-Path .\tmp\caddy-validation\caddy.exe).Path
uv run --project apps/api pytest tests/security/test_caddy_contract.py tests/security/test_caddy_runtime.py -q
6 passed
```

The Caddy runtime test uses independent loopback mock web/API upstreams and
proves the `/api/*` split, frontend fallback, safe upstream failure, and
no-store behavior. The service-level API tests prove a complete mock job,
capability-token access, preview/download publication, failure handling, and
the public `running` vocabulary.

## Browser and operator gates

- Playwright's isolated API now uses test-only port `127.0.0.1:18000`, leaving
  the live API on `:8000` untouched. Chromium was installed locally and all
  five configured browser tests passed.
- The real RTX 5070/ComfyUI flow is recorded below from a controlled local
  Caddy run. No generated artifact or private URL is stored in this evidence.
- Quick Tunnel trials remain operator actions after the Caddy service is
  installed and the local listener boundary is corrected.

## Continuation evidence (2026-09-06)

The local Caddy binary was run in the foreground using the validated
configuration and loopback environment variables. No Windows service was
installed or modified.

```text
GET http://127.0.0.1:8080/                    -> 200
GET http://127.0.0.1:8080/api/v1/health/live  -> 200 {"status":"ok"}
GET http://127.0.0.1:8080/api/v1/health/ready -> 200 {"status":"ok"}
GET http://127.0.0.1:8080/api/v1/health/engine -> 200 {"status":"ok"}
```

One controlled real generation was submitted through Caddy using the approved
Hunyuan3D textured-GLB manifest and the project fixture image. The job reached
`processing` and then `completed` with `progress_percent=100`.

```text
model response: 200
download response: 200
GLB bytes: 3,664,916
model SHA-256: dad940c5c6269e9857c573c3d2b82451e6ee2522d63d5aaed769041c610d4d50
download SHA-256: dad940c5c6269e9857c573c3d2b82451e6ee2522d63d5aaed769041c610d4d50
model/download bytes equal: True
GLB magic: glTF
```

The job token and temporary credentials are intentionally omitted. This is
local-through-Caddy evidence only; Quick Tunnel and off-campus acceptance were
not performed.

## Near-limit real service flow (2026-09-07)

The feature-004 local acceptance verifier inserted a private ancillary PNG
chunk into the approved fixture, preserving the visible image while producing
a valid **10,484,736-byte** upload (1 KiB below the 10 MiB application limit).
It submitted the image through `http://127.0.0.1:8080` after confirming the
ComfyUI queue was empty.

```text
POST /api/v1/jobs: 201 in 0.109 seconds
Observed states: queued -> running -> completed
Preview: 200
Download: 200
GLB bytes: 4,245,776
Preview/download equal: true
SHA-256: e99f491eab68fa74f01323141b00ed721e1234dba70a7874174bc0a86c47fa57
GLB magic: glTF
```

The local listener inventory immediately before final validation showed ports
3000, 8000, 8080, and 8188 bound only to `127.0.0.1`. Capability data and input
content are intentionally omitted. After an elevated `Local3D-ComfyUI`
restart loaded the approved smoke-node whitelist, the CRLF-safe verifier passed
against the running engine. All four Local3D services were running afterward
and the local health chain returned true for Caddy, Web, API, Storage,
Workflow, ComfyUI, GPU, ListenerBoundary, and ProcessBoundary. QuickTunnel and
PublicRoute were correctly false because no temporary public session was
running.
