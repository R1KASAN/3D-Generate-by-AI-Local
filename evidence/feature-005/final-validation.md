# Feature 005 final validation snapshot

Validation timestamp (UTC): `2026-09-09T08:25:08Z`.

## Task accounting

- Starting state for this pass: **84/107 completed**.
- Completed during this pass: **T097**.
- Current state: **85/107 completed; 22 remaining**.

## Local validation completed

- API/security/contract suite: **287 passed, 7 skipped**, exit 0.
- Ruff: **PASS**.
- mypy: **PASS**.
- Frontend unit: **29 passed**.
- Frontend typecheck: **PASS**.
- Frontend lint: **PASS**.
- Direct isolated Playwright: **11 passed**.
- Test-only Nginx Playwright mode: **11 passed**; frontend 3100 → Nginx
  18000 → mock API 18001; production ports were unchanged.
- Nginx runtime failure-boundary tests: **2 passed**.
- Nginx service configuration: `nginx.exe -t` **successful** using
  `C:\ProgramData\Local3D\nginx\nginx.conf`.
- PowerShell parsing: **23 scripts parsed successfully**.
- Frontend package build/validator: static tree and archive **valid**.
- Linux package portability regression: **6 passed**; rebuilt release ZIP has
  24 POSIX-named entries, file mode `0100644`, zero backslash member names, and
  SHA-256 `472D988BEC81333CBC505B2C020EFC4335C02841AFE801BB22384C072E65929E`.
- Local failure matrix: **5/5 cases passed**, leak scans passed.
- Real local Nginx flow: one approved workflow completed through
  Nginx → FastAPI → ComfyUI → RTX 5070; queued → running → completed;
  preview/download both HTTP 200, identical GLB, 3,736,992 bytes, valid
  `glTF` magic, SHA-256 recorded in `us1-local-real.md`.
- Feature 005 health chain: Nginx/API/storage/workflow/ComfyUI/GPU,
  listener and process boundaries healthy. Named Tunnel and Stable Public API
  correctly remain false because they are not configured.
- Firebase frontend-only preview: temporary channel deployed; `/` redirects
  to `/mango74/`, the application and static assets return HTTP 200, and a
  headless browser reports an understandable AI-service-unavailable state when
  the stable API hostname cannot be resolved. No Firebase-origin CORS
  permission or production configuration was enabled.

## This pass commands

- `npm test --prefix apps/web` — 29 passed.
- `npm run typecheck --prefix apps/web` — PASS.
- `npm run lint --prefix apps/web` — PASS.
- `npm run test:e2e --prefix apps/web` — 11 passed.
- `E2E_NGINX=1 npm run test:e2e --prefix apps/web` — 11 passed.
- `uv run --project .\apps\api pytest -q` — 287 passed, 7 skipped, exit 0.
- `uv run --project .\apps\api ruff check apps/api/src tests scripts` — PASS.
- `uv run --project .\apps\api mypy apps/api/src` — PASS.
- PowerShell parser over 23 scripts — 0 parse errors.
- Nginx syntax validation against `C:\ProgramData\Local3D\nginx\nginx.conf`
  — successful.
- Firebase preview artifact build and temporary channel deploy — PASS; the
  detailed route/browser evidence is in `firebase-preview-disabled.md`.
- Current named-Tunnel prerequisite check: `Get-Service cloudflared` returned
  `NOT_FOUND` and `Resolve-DnsName mango74-api.mangosgo.com` returned
  `UNRESOLVED`; no connector token or DNS record was inferred or recorded.
- `verify_named_tunnel.ps1 -ApiHealthUrl https://mango74-api.mangosgo.com/api/v1/health/live`
  returned `ServiceRunning=false`, `StatusCode=null`, `Healthy=false` (exit 1),
  which is the expected blocked result before administrator activation.
- The recovery runner was preflighted without restarting anything. It stopped
  safely with `BLOCKED: required restart services are not installed: cloudflared`;
  no restart trial was counted.

## Not production-ready yet

The remaining gates require authorized systems or a separate network:

- named Cloudflare Tunnel and stable API hostname;
- NT Server frontend deployment, baseline, and rollback;
- independent-network acceptance and public-boundary verification;
- production refresh/cancellation and Tunnel outage trials;
- three restart trials including cloudflared;
- Firebase preview permission-on/removal trial (T098).

No DNS, direct inbound Notebook port, public FastAPI/ComfyUI port, or raw
Notebook-IP route was added. No external or reboot result was inferred.

## Remaining task classification

**MANUAL:** T042, T043, T044, T051, T052, T062, T066, T068, T069, T070,
T082, T084, T085, T086, T087, T088, T098, T103

**BLOCKED:** T083 (requires T082 named Tunnel), T089 (requires an approved
production rollback baseline), T090 (requires T082–T089 evidence)

**NOT REACHED:** T067 (requires administrator-confirmed NT deployment details
from T066)

**FAILED:** none.

Overall decision: **NO-GO for production** until the remaining manual gates
have real evidence.
