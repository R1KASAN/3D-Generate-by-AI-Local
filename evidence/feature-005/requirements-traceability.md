# Feature 005 traceability (implementation snapshot)

| Area | Implementation/test evidence | Status |
|---|---|---|
| Static split-origin frontend | `apps/web/next.config.ts`, `scripts/windows/build_frontend_package.ps1`, package contract tests | PASS locally |
| Stable API and exact CORS | `apps/web/lib/config/public-runtime.ts`, `apps/api/src/local3d/config.py`, CORS tests | PASS locally |
| Nginx loopback origin | `deploy/nginx/nginx.conf`, Nginx contract/runtime test (runtime requires operator binary) | STATIC PASS / RUNTIME GATED |
| Durable jobs/tokens/cancellation | existing job service plus Feature 005 contract, unit, and E2E tests | PASS locally |
| Named Tunnel/NT deployment | `deploy/cloudflared/named-tunnel.md`, runbooks, external evidence gates | ADMIN GATE |
| Production acceptance/rollback | quickstart and runbooks | ADMIN + EXTERNAL GATE |

No external deployment or production GPU claim is made by this local snapshot.
