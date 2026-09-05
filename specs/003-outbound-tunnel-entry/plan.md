# Implementation Plan: Zero-Cost Local AI Public Server

**Branch**: `003-outbound-tunnel-entry` | **Date**: 2026-09-06 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/003-outbound-tunnel-entry/spec.md`

## Summary

Promote the LAN-only feature 001 service to a public AI server by replacing feature 002's **inbound** origin proxy with an **outbound** Cloudflare Tunnel connector on the approved origin. The origin becomes thin and stateless: `cloudflared` plus a loopback-bound streaming reverse proxy. The entire feature 001 application — job service, serial queue, SQLite state, uploads, artifacts, retention, AI engine — stays on the GPU laptop behind the existing narrow WireGuard binding.

Three structural changes drive most of the work:

1. **No inbound listener anywhere.** `cloudflared` dials out, so the origin's public `:443` listener, the Cloudflare Origin CA certificate, and Authenticated Origin Pulls from feature 002 are all removed rather than reconfigured. This deletes an entire class of operator-managed secrets (FR-003, FR-006).
2. **The LAN-only startup deadlock is fixed.** `deploy/windows/services/web.xml` currently binds Next.js to `10.10.0.2` *and* declares `<depend>WireGuardTunnel$upstream</depend>`, so a WireGuard failure prevents the LAN workflow from starting at all — violating FR-037. Services move to loopback binding with the private binding adding a route, never gating startup (FR-023a, FR-023d).
3. **Evidence becomes provider-scoped.** Origin-path proof and TLS-termination disclosure differ between the Cloudflare primary route and the zrok degraded fallback, so verification is written per active provider rather than once (FR-002a, FR-011e, FR-018).

Production cutover is gated on `mangosgo.com` authorization; **no other work is gated** (FR-012a). A Quick Tunnel carries interim external testing.

## Technical Context

**Language/Version**: Python 3.12 (FastAPI job service, verification scripts), TypeScript/Next.js (browser client) — both unchanged from feature 001. Deployment logic is PowerShell on the GPU laptop; origin-side scripting language is deferred pending OS confirmation.

**Primary Dependencies**: `cloudflared` (outbound connector, replaces inbound proxy role), Caddy (loopback streaming pass-through, reused from feature 002 with the inbound listener removed), WireGuard (existing private binding, unchanged), WinSW (GPU-laptop service supervision, existing).

**Storage**: SQLite on the GPU laptop only. The approved origin stores no job state, uploads, or artifacts (FR-014). Origin persistence is limited to connector credentials, proxy configuration, and masked operational logs.

**Testing**: pytest for contract and security tests (`tests/security/`, `apps/api/tests/`), Playwright for browser E2E (`apps/web/tests/e2e/`), and `scripts/verify/` for network-boundary and acceptance evidence. Reboot, recovery, and egress verification remain operator-executed with captured evidence per Constitution II.

**Target Platform**: GPU laptop is Windows 11 with an RTX 5070 Laptop GPU (evidenced). **Approved origin OS is NEEDS CLARIFICATION** — unverified until physical inspection of the lab server; design must be OS-independent with provisional per-OS operator steps.

**Project Type**: Split-host deployment layer over an existing web application. No new application services.

**Performance Goals**: Public health route restored within 5 minutes of network readiness after reboot (SC-006/006a/006b); project-controlled unavailable response within 5 seconds when compute is down (SC-008); streaming pass-through adds no whole-file transfer delay (FR-014a).

**Constraints**: Zero project-attributable cost (FR-007, FR-008); no inbound public port (FR-003); origin holds no job state (FR-014); GPU concurrency remains one (FR-021); 10 MiB uploads and 24-hour retention unchanged (FR-019, FR-028); interim Quick Tunnel testing capped at 200 concurrent requests and no SSE (FR-012b).

**Scale/Scope**: Single origin, single GPU laptop, one serial queue. Realistic load is far below the 5 GB/day zrok fallback quota and the Cloudflare free-plan boundary.

## Constitution Check

*GATE: evaluated against constitution v1.2.0 before Phase 0 and re-checked after Phase 1.*

| Principle | Status | Notes |
|---|---|---|
| I. Smallest Verified Vertical Slice | **PASS** | Deployment-layer slice only. No payment, Kubernetes, Redis, cloud GPU, or object storage introduced. |
| II. Evidence-Gated Completion | **PASS** | Every hardware-, network-, and reboot-dependent claim is operator-executed with captured evidence. Origin OS stays `PENDING` rather than assumed. |
| III. Security and Private-Service Boundary | **PASS (stricter)** | The constitution permits HTTPS/443 as the sole Internet-facing entry. This design exposes **no inbound port at all** — a strict tightening, not a deviation. Capability-token policy (b) is unchanged. TLS-terminating third party is disclosed per FR-018, now provider-scoped so the disclosure stays accurate if zrok carries traffic. |
| IV. Job and File Isolation | **PASS** | Untouched; all job state remains on the GPU laptop under feature 001's rules. |
| V. Single-GPU Queue Correctness | **PASS** | Concurrency remains one. The origin adds no queueing or retry that could duplicate work. |
| VI. Replaceable Integration Boundary | **PASS** | The origin is a transparent streaming proxy; it introduces no engine identifiers into the public API. |
| VII. Cross-Platform Development Discipline | **PASS, with active risk** | Origin OS unverified. Phase 0 mandates an OS-independent contract with per-OS operator steps kept provisional. |
| VIII. Test-First Critical Behavior | **PASS** | Contracts and boundary tests precede configuration changes; manual procedures retained where automation is impossible. |
| IX. Ownership-Critical Decisions | **PASS, two open inputs** | Hostname authorization and the degraded-fallback recovery window are recorded as owner inputs and block only cutover, not implementation. |
| X. Scope and Simplicity | **PASS** | Net component count **decreases**: the inbound listener, Origin CA certificate, and Authenticated Origin Pulls are removed. `cloudflared` is the only addition. |

**No violations requiring justification.** Complexity Tracking is intentionally empty.

## Project Structure

### Documentation (this feature)

```text
specs/003-outbound-tunnel-entry/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── origin-entry.md      # cloudflared + loopback pass-through contract
│   ├── compute-link.md      # WireGuard binding, revised for LAN independence
│   ├── health-chain.md      # Layered health and recovery contract
│   └── evidence-methods.md  # Provider-scoped origin-path and TLS evidence
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
deploy/
├── cloudflared/                  # NEW — connector config, credential handling, service units
│   ├── config.yml.example
│   ├── README.md
│   └── services/                 # provisional per-OS unit/service definitions
├── caddy/                        # REVISED — loopback listener, inbound :443 + mTLS removed
│   ├── Caddyfile
│   ├── .env.example
│   └── maintenance/maintenance.html
├── wireguard/                    # UNCHANGED — existing narrow private binding
└── windows/services/
    ├── web.xml                   # REVISED — remove 10.10.0.2 bind and WireGuard <depend>
    ├── api.xml                   # verified loopback-bound
    └── comfyui.xml               # verified loopback-bound

scripts/
├── windows/                      # GPU-laptop start/recovery, revised for LAN independence
│   ├── start_web_service.ps1     # REVISED — drop tunnel-address gating
│   └── health_chain.ps1          # NEW — per-layer health probes
└── verify/                       # REVISED + NEW — boundary and acceptance evidence
    ├── test_origin_lockdown.py   # REVISED — no inbound listener expected at all
    ├── test_egress_identity.py   # NEW — provider-scoped approved-address proof
    └── test_lan_independence.py  # NEW — LAN works with binding down

tests/security/
├── test_caddy_contract.py        # REVISED — loopback-only, streaming, no buffering
└── test_compute_link_startup.py  # REVISED — startup must not gate on the binding

docs/operations/                  # REVISED runbooks; EU.org/inbound-era content retired
evidence/public-deployment/       # Cutover evidence set, provider-scoped
```

**Structure Decision**: No new application tier. Work concentrates in `deploy/`, `scripts/`, `tests/security/`, `docs/operations/`, and `evidence/`. The only application-adjacent change is removing the private-address binding from the web service so feature 001 starts without WireGuard. `apps/api` and `apps/web` source logic is otherwise untouched, satisfying the spec's "preserve feature 001" constraint.

## Complexity Tracking

> No Constitution Check violations. This section is intentionally empty.
