# Feature 004 validation — implementation pass

This is a truthful validation record, not a release claim. The user-provided
starting state was 51/81; the repository ledger at the start of this pass was
67/81. After the validated work below, the ledger is **71/81 completed** with
10 environment-dependent tasks still open.

## Commands executed and results

### API, contract, and security suites

```text
uv run --project apps/api pytest apps/api/tests tests/security -q
239 passed, 5 skipped in 15.36s

Push-Location apps/api; uv run pytest
149 passed, 4 skipped in 14.50s
uv run ruff check .
All checks passed!
uv run mypy src
Success: no issues found in 34 source files

uv run --project apps/api pytest apps/api/tests/integration/test_orphan_cleanup.py -q
5 passed

uv run --project apps/api python scripts/verify/validate_contracts.py \
  specs/004-secure-ai-test-access/contracts/openapi.yaml \
  workflows/hunyuan3d/workflow-manifest.json
PASS: both contract artifacts

uv run --project apps/api python scripts/verify/test_log_redaction.py --root . --require-evidence
PASS
```

The orphan-cleanup additions cover crash-created UUID directories, shared
storage locking, and low-storage admission without deleting accepted work.

### Frontend

```text
npm test --prefix apps/web -- --run
3 test files, 16 tests passed
npm run typecheck --prefix apps/web
PASS
npm run lint --prefix apps/web
PASS
npm run build --prefix apps/web
PASS (Next.js production build)
```

The frontend now explicitly reports a completed job with no result artifact as
unavailable and does not offer a download button.

### Playwright browser validation

```text
npm run test:e2e --prefix apps/web
5 passed, 0 failed, 0 skipped (9.6s)
```

Chromium was installed with the existing Playwright version. The suite uses a
disposable mock API on `127.0.0.1:18000`; production FastAPI remains on
`127.0.0.1:8000`. No real GPU work is submitted by browser tests.

### Caddy and static scripts

```text
tmp/caddy-validation/caddy.exe fmt --diff deploy/caddy/Caddyfile
PASS (no formatting changes required)
tmp/caddy-validation/caddy.exe validate --config deploy/caddy/Caddyfile --adapter caddyfile
Valid configuration
uv run --project apps/api python scripts/verify/verify_comfy_manifest.py \
  workflows/hunyuan3d/workflow-manifest.json \
  --comfy-root C:\Users\MetaHosP\ComfyUI --base-url http://127.0.0.1:8188
FAIL: Hy3D21ShapeSmokeOffloadMeshGen is not registered; editable workflow hash differs
```

PowerShell parsing and the Windows operator-contract tests remain passing from
the baseline. The manifest failure is retained as a real environment blocker;
it was not converted into a skip or a false pass.

### Local service-chain and Quick Tunnel

Foreground Caddy previously served `/`, `/api/v1/health/live`,
`/api/v1/health/ready`, and `/api/v1/health/engine` with HTTP 200. During that
controlled interval `health_chain.ps1 -Json` reported Caddy/Web/API/Storage/
Workflow/ComfyUI/GPU/ProcessBoundary true. The normal current-state health
report is not green because `Local3D-Caddy` is not installed/running and the
operator-owned portproxy mappings keep ListenerBoundary false.

A Quick Tunnel was previously started only after the foreground Caddy check.
Cloudflare issued a random temporary `trycloudflare.com` URL; same-machine
requests to `/` and `/api/v1/health/live` returned 200 and the health report
showed QuickTunnel/PublicRoute true. The temporary hostname was stopped and
not persisted. This is local-through-tunnel evidence, not off-campus proof.

## Existing real RTX evidence

One approved Hunyuan3D textured-GLB run already completed through foreground
Caddy → FastAPI → ComfyUI → RTX 5070. The 3,664,916-byte GLB had magic `glTF`;
authenticated preview and download both returned 200 and matched SHA-256
`dad940c5c6269e9857c573c3d2b82451e6ee2522d63d5aaed769041c610d4d50`. No GPU
run was repeated in this pass.

## Boundary and service observations

- FastAPI, Web, and ComfyUI application listeners are loopback-bound; no
  application listener was changed to `0.0.0.0` or `161.200.90.4`.
- `Local3D-API`, `Local3D-ComfyUI`, and `Local3D-Web` are installed/running.
  `Local3D-Caddy` is not installed in the current non-elevated session.
- `netsh interface portproxy show all` still reports operator-owned mappings
  `172.20.10.6:3000 -> 127.0.0.1:3000` and
  `10.203.231.203:3000 -> 127.0.0.1:3000`; they were not modified.
- No domain, DNS, named Tunnel, direct inbound rule, WireGuard dependency,
  second server, cloud GPU, credentials, or live temporary URL was added.

## Remaining task ledger

Current count: **71 completed / 81 total; 10 remaining**.

| Classification | Task IDs |
| --- | --- |
| BLOCKED | T034, T074 (off-campus network and dependent public-boundary gates) |
| MANUAL | T066, T072, T073 (elevated service operations, controlled restart/reboot) |
| FAILED | T079 (the required ComfyUI manifest verifier was executed and failed on a missing registered node and editable-workflow hash mismatch) |
| NOT REACHED | T030 (complete near-limit local flow), T049 (complete failure matrix), T053 (full browser isolation criteria), T057 (five-user plus two-job real-GPU trial) |

Constitution and security audits are recorded in `constitution-audit.md` and
`security-audit.md`; those tasks are complete because the audits explicitly
record blockers instead of hiding them.

## Next operator actions

Run only with approval/elevation where applicable:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/windows/install_winsw_services.ps1 `
  -ProjectRoot (Get-Location).Path `
  -WinSWPath C:\path\to\WinSW-x64.exe `
  -ExpectedWinSWSha256 <64-hex-sha256> `
  -StartServices
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/windows/verify_services.ps1 -ProjectRoot (Get-Location).Path

netsh interface portproxy show all
# Only after explicit approval:
netsh interface portproxy delete v4tov4 listenaddress=172.20.10.6 listenport=3000
netsh interface portproxy delete v4tov4 listenaddress=10.203.231.203 listenport=3000

powershell -NoProfile -ExecutionPolicy Bypass -File scripts/windows/verify_reboot_recovery.ps1 `
  -ProjectRoot (Get-Location).Path -ExecuteReboot

uv run --project apps/api python scripts/verify/test_external_acceptance.py `
  --hostname <actual-temporary-hostname> `
  --image fixtures/inputs/valid-reference.png `
  --confirm-off-campus `
  --evidence evidence/feature-004/us1-public.md
```

Do not report the feature complete until the remaining runtime and external
acceptance gates have real evidence.

## Operator follow-up: Caddy service and Quick Tunnel boundary (2026-09-07)

The operator installed the four planned WinSW services from the hash-verified
wrapper, copied the validated Caddy 2.11.4 binary into the service directory,
and started `Local3D-Caddy`. All four services reported `Running`.

```text
GET http://127.0.0.1:8080/                    -> 200
GET http://127.0.0.1:8080/api/v1/health/live  -> 200 {"status":"ok"}
```

The two legacy operator-owned portproxy mappings were explicitly removed by
the operator. A subsequent `health_chain.ps1 -Json` reported
`Caddy=true`, `Web=true`, `Api=true`, `Storage=true`, `Workflow=true`,
`ComfyUI=true`, `GPU=true`, `ListenerBoundary=true`, and
`ProcessBoundary=true`; QuickTunnel/PublicRoute were false until the next
temporary session.

One temporary Quick Tunnel session then returned HTTP 200 for both the public
root and public `/api/v1/health/live`, and the health report showed
`QuickTunnel=true`, `PublicRoute=true`, and `ListenerBoundary=true`. The
operator stopped it with `stop_quick_tunnel.ps1 -Elevate`; verification found
zero `cloudflared` processes, no state file, and local API health still HTTP
200. The random hostname is intentionally omitted and must not be reused
after the connector stops; an old hostname returning Cloudflare Error 1033 is
expected behavior.

## Continuation validation (2026-09-07)

```text
uv run --project apps/api pytest -q                 -> 244 passed, 5 skipped
uv run --project apps/api pytest tests -q            -> 95 passed, 1 skipped
uv run --project apps/api ruff check .               -> PASS
uv run --project apps/api mypy src                   -> PASS (34 files)
npm run test --prefix apps/web                       -> 16 passed
npm run typecheck --prefix apps/web                  -> PASS
npm run lint --prefix apps/web                       -> PASS
npm run build --prefix apps/web                      -> PASS
npm run test:e2e --prefix apps/web                   -> 5 passed
validate_contracts.py (OpenAPI + manifest)           -> PASS
verify_comfy_manifest.py (live ComfyUI)              -> PASS
Caddy validate (8080 loopback config)                -> PASS
PowerShell parser (all scripts/windows/*.ps1)        -> 0 errors
health_chain.ps1 -Json                               -> local layers PASS
```

Playwright used isolated API port 18000 and the mock adapter; it did not submit
GPU work. The API suite emitted only a Windows pytest temporary-directory
cleanup permission warning at process exit after the passing result.

T030 recorded one real near-limit Caddy flow: 10,484,736-byte PNG, HTTP 201 in
0.109 seconds, `queued -> running -> completed`, preview/download HTTP 200,
equal bytes, valid `glTF` magic, and SHA-256
`e99f491eab68fa74f01323141b00ed721e1234dba70a7874174bc0a86c47fa57`. The
approved Hunyuan3D manifest verifier passed after the elevated ComfyUI restart
loaded `local3d_smoke_nodes.py` in the whitelist.

T049 now includes mock invalid/pressure/low-disk/timeout/cancellation/
missing-corrupt-output/orphan cases plus controlled Caddy, Web, API, and
ComfyUI restarts. T057 records the five-user local trial and existing two-job
real RTX serial evidence. T072 records forced layer failures, clean stop/start,
no Quick Tunnel, and preserved SQLite/storage data.

## Current task ledger

**79 completed / 81 total; 2 remaining.**

| Classification | Task IDs | Reason |
|---|---|---|
| BLOCKED | T034, T074 | Require a genuine external/off-campus network; T074 also requires the completed T073 evidence. |

No direct probe to `161.200.90.4` was executed. Application listeners remain
loopback-only and no portproxy, DNS, domain, inbound rule, WireGuard, or second
server was added.

The redaction scanner also passed with a unique sentinel not present in the
documentation examples:

```text
python scripts/verify/test_log_redaction.py --root . \
  --sentinel FEATURE004-SENTINEL-NOT-PRESENT-20260907 --require-evidence
-> PASS
```

## Re-entry precheck (2026-09-07)

The four planned Windows services were checked again and all reported
`Running`. `health_chain.ps1 -Json` again reported healthy Caddy, Web, API,
storage, workflow, ComfyUI, GPU, listener-boundary, and process-boundary
layers. Ports 3000, 8000, 8080, and 8188 were listening only on
`127.0.0.1`; `netsh interface portproxy show all` returned no mappings.
Quick Tunnel/PublicRoute remained false because no temporary tunnel was
running. The operator subsequently completed the numbered Trial 1, Trial 2
(queued), and Trial 3 Notebook restart records; all three recovery verdicts
are PASS in `evidence/feature-004/us4-restart.md`. No external-network test
was performed during this continuation.

## External acceptance preparation (2026-09-07)

The local chain passed before a Quick Tunnel launch. Cloudflare cloudflared
prechecks reported DNS, UDP/QUIC, TCP/HTTP2, and Cloudflare API connectivity
as PASS, with the origin configured as `http://127.0.0.1:8080`. The launcher
session used by this validation process then terminated with its terminal, so
the temporary hostname was not retained and no T034/T074 acceptance evidence
was claimed. A fresh launcher must remain open while the operator runs the
external tests from a genuinely off-campus network.

## Queued-job owner cancellation (2026-09-07)

Implemented a token-authorized, durable and idempotent
`POST /api/v1/jobs/{job_id}/cancel` operation. It removes only a waiting job
from the in-process dispatcher and persists `cancelled` in SQLite. A job whose
engine submission is already reserved returns a safe `409`; the public route
does not interrupt active ComfyUI/GPU work. The browser exposes the action only
for `queued` and restores the owner credential from per-tab session storage
after refresh.

```text
uv run --project apps/api pytest apps/api/tests tests/security -q
-> 248 passed, 5 skipped

uv run --project apps/api ruff check apps/api/src apps/api/tests
-> PASS

uv run --project apps/api mypy apps/api/src/local3d
-> PASS (34 source files)

npm test --prefix apps/web -- --run
-> 17 passed

npm run typecheck --prefix apps/web
npm run lint --prefix apps/web
npm run build --prefix apps/web
-> PASS

npm run test:e2e --prefix apps/web
-> 6 passed, including refresh then owner cancellation

uv run --project apps/api python scripts/verify/validate_contracts.py \
  specs/004-secure-ai-test-access/contracts/openapi.yaml \
  workflows/hunyuan3d/workflow-manifest.json
-> PASS
```

The first full E2E run had one timing-sensitive failure in the existing queue
position isolation case (the new cancellation case passed). That isolation
case passed when rerun alone, and the subsequent complete six-test E2E run
passed. No real GPU job was submitted for this change.

Deployment restart was attempted only after verifying ComfyUI had no running
or pending work. The workspace contained 12 durable queued rows, which were
not modified. The current non-elevated session could not stop the WinSW Caddy
service, so the validated code/build requires an Administrator service restart
before the live Caddy/Quick Tunnel route exposes the new operation.

## Operator-requested queue reset (2026-09-07)

The operator explicitly requested removal of all waiting jobs. Read-only
prechecks initially observed 10 `queued`, 1 `processing`, and one active
ComfyUI execution with no ComfyUI pending work. During the interval before the
transaction, the active job completed and the dispatcher promoted the next
waiting job. The bounded SQLite transaction therefore deleted all 9 rows that
were still `queued`; foreign-key cascades removed their assets/events and the
9 corresponding UUID-scoped storage directories were deleted. The resulting
durable state contained zero queued rows, while the one already-processing job
was deliberately left untouched. A non-elevated session could not restart the
WinSW service chain, so an Administrator restart remains required after the
active job finishes to discard stale in-memory queue references.
