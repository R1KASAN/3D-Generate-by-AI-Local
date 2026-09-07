# Feature 004 Baseline Evidence

Date: 2026-09-06

This baseline was captured before implementation changes. No credentials,
temporary public URLs, user content, generated assets, or environment-specific
private configuration are recorded here.

## Repository state

- Branch: `main`
- Existing user-owned dirty paths were preserved; implementation did not reset
  or delete them.
- The active repository Caddy configuration is still feature-003-shaped and
  listens on `:8443` with a remote/WireGuard upstream. It is not accepted as
  feature-004 evidence.
- The existing cloudflared example is a named-tunnel/custom-hostname template.
  It is not accepted as feature-004 evidence.

## Tool versions

- Python: 3.12.10
- pytest: 8.4.1
- Node.js: 24.19.0
- npm: 11.17.0
- Vitest: 4.1.11
- Caddy: repository-local validation binary exists at
  `tmp/caddy-validation/caddy.exe` (PATH lookup was unavailable)

## Baseline commands

| Command | Result |
|---|---|
| `uv run pytest` from `apps/api` | PASS — 131 passed, 4 skipped |
| `npm test` from `apps/web` | PASS — 3 files, 8 tests; Vite native-loader warning only |
| `npm run typecheck` from `apps/web` | PASS |
| `npm run lint` from `apps/web` | PASS |
| `caddy validate --config deploy/caddy/Caddyfile --adapter caddyfile` | BLOCKED — `caddy` is not on PATH; use the repository-local binary after the feature-004 Caddyfile is implemented |

## Scope boundary

The approved implementation remains one Notebook/PC. Application listeners
must remain loopback-only on ports 3000, 8000, 8080, and 8188. Public testing
will be added only after local routing and AI validation pass.
