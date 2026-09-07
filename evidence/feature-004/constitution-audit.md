# Feature 004 Constitution Audit

Date: 2026-09-07

## Decision

No unapproved architecture or governance exception was found. The
implementation remains a single Notebook/PC with loopback services and an
outbound-only Cloudflare Quick Tunnel. The release is **not yet accepted**
because external-network, elevated-service, and reboot gates remain open.

## Principle mapping

| Constitution principle | Evidence / result |
| --- | --- |
| I. Single-node architecture | `spec.md`, `plan.md`, `deploy/caddy/Caddyfile`, service scripts, and architecture contract tests keep Caddy, API, ComfyUI, storage, and GPU on one Notebook. No second server was added. |
| II. Outbound-only connectivity | Quick Tunnel was exercised against `127.0.0.1:8080`; no direct public ingress was configured. External negative probes and firewall confirmation remain operator-gated. |
| III. Local isolation | Caddy routes `/` to `127.0.0.1:3000` and `/api/*` to `127.0.0.1:8000`; ComfyUI remains an API-only dependency on `127.0.0.1:8188`. Contract, runtime, and listener checks pass for application bindings. |
| IV. Environment separation | Temporary Quick Tunnel is documented as non-production; no custom hostname, DNS record, or domain purchase was made. |
| V. Security and secrets | Token authorization, redaction tests, input validation, atomic result handling, and repository scans pass. Test placeholders in docs/fixtures are not live credentials or live URLs. |
| VI. Reliability/resource control | Job lifecycle, single-worker admission, timeouts, restart reconciliation, orphan cleanup, low-storage rejection, and health reporting are covered by API/integration tests. Full reboot and controlled real failure matrix remain open. |
| VII. Testing/observability | API/security, frontend unit, Playwright, Caddy, contract, and PowerShell validations have recorded results in `final-validation.md`. Hardware and network claims are not inferred from mock tests. |
| VIII. Scope control | No WireGuard, second server, cloud GPU, direct inbound rule, named tunnel, DNS, or production hostname was introduced. Open work is classified rather than hidden. |

## Requirements and success criteria

FR-001–FR-027 are implemented by the approved spec/plan contracts and the
passing API/security and routing suites; FR-022 and SC-009 remain dependent on
the manual reboot trials. SC-001–SC-010 and SC-012 are locally covered or have
recorded evidence; SC-005, SC-008, SC-009, SC-011, and SC-013 still require the
specific concurrency, failure-injection, reboot, external-network, or repeated
Quick Tunnel evidence stated in `tasks.md`. SC-014 is covered by the temporary
test notices and operator documentation.

## Open gates

The remaining open gates are environmental, not architecture exceptions:
WinSW installation/elevation, operator-owned portproxy retirement, controlled
Notebook restart/reboot, external/off-campus acceptance, and the complete
multi-condition failure/concurrency trials. These are left unchecked in
`tasks.md` and classified in `final-validation.md`.
