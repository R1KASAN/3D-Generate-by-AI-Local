# Implementation Plan: Zero-Cost Local AI Public Server

**Branch**: `003-outbound-tunnel-entry` | **Date**: 2026-09-06 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/003-outbound-tunnel-entry/spec.md`

## Summary

Promote the LAN-only feature 001 service to a public AI server by replacing feature 002's **inbound** origin proxy with an **outbound** Cloudflare Tunnel connector on the approved origin. The origin becomes thin and stateless: `cloudflared` plus a loopback-bound streaming reverse proxy. The entire feature 001 application — job service, serial queue, SQLite state, uploads, artifacts, retention, AI engine — stays on the GPU laptop behind the existing narrow WireGuard binding.

Three structural changes drive most of the work:

1. **No inbound application or management listener anywhere.** `cloudflared` dials out, so the origin's public `:443` listener, the Cloudflare Origin CA certificate, and Authenticated Origin Pulls from feature 002 are all removed rather than reconfigured. The compute-link contract separately permits only its authenticated WireGuard UDP transport listener. This deletes an entire class of operator-managed secrets (FR-003, FR-006).
2. **The LAN-only startup deadlock is fixed.** `deploy/windows/services/web.xml` currently binds Next.js to `10.10.0.2` *and* declares `<depend>WireGuardTunnel$upstream</depend>`, so a WireGuard failure prevents the LAN workflow from starting at all — violating FR-037. Services move to loopback binding with the private binding adding a route, never gating startup (FR-023a, FR-023d).
3. **Evidence becomes provider-scoped.** Origin-path proof and TLS-termination disclosure differ between the Cloudflare primary route and the zrok degraded fallback, so verification is written per active provider rather than once (FR-002a, FR-011e, FR-018).

4. **The private-link transport boundary is in scope, not inherited.** Feature 002 never needed the origin to answer an inbound socket, so its WireGuard posture was carried forward untested. Option A permits exactly one narrowly scoped WireGuard UDP transport listener on the approved origin, which makes that boundary a feature-003 obligation with its own configuration, verifier, negative test, and live evidence (SC-018). Option A is itself conditional: if the origin cannot receive that UDP transport directly without router port forwarding, Option A is not feasible for this target and the transport must be redesigned (FR-041).

Production cutover is gated on `mangosgo.com` authorization, on the SC-018 transport-boundary evidence, and on the FR-041 reachability precondition; **no other work is gated** (FR-012a). A Quick Tunnel carries interim external testing.

## Technical Context

**Language/Version**: Python 3.12 (FastAPI job service, verification scripts), TypeScript/Next.js (browser client) — both unchanged from feature 001. Deployment logic is PowerShell on the GPU laptop; origin-side scripting language is deferred pending OS confirmation.

**Primary Dependencies**: `cloudflared` (outbound connector, replaces inbound proxy role), Caddy (loopback streaming pass-through, reused from feature 002 with the inbound listener removed), WireGuard (existing private binding; its **transport boundary on the approved origin is in scope for this feature**, per contracts/compute-link.md C1a and SC-018 — the addressing carries forward, the firewall and listener posture does not), WinSW (GPU-laptop service supervision, existing).

**Storage**: SQLite on the GPU laptop only. The approved origin stores no job state, uploads, or artifacts (FR-014). Origin persistence is limited to connector credentials, proxy configuration, and masked operational logs.

**Testing**: pytest for contract and security tests (`tests/security/`, `apps/api/tests/`), Playwright for browser E2E (`apps/web/tests/e2e/`), and `scripts/verify/` for network-boundary and acceptance evidence. Reboot, recovery, and egress verification remain operator-executed with captured evidence per Constitution II.

**Target Platform**: GPU laptop is Windows 11 with an RTX 5070 Laptop GPU (evidenced). **Approved origin OS is `PENDING TARGET INSPECTION`** — this is missing physical evidence, not an unresolved architecture decision; the design is OS-independent and per-OS operator steps stay provisional. Recorded by tasks.md T065 (origin OS, version, egress address) and research.md R1.

**Project Type**: Split-host deployment layer over an existing web application. No new application services.

**Performance Goals**: Public health route restored within 5 minutes of network readiness after reboot (SC-006/006a/006b); project-controlled unavailable response within 5 seconds when compute is down (SC-008); streaming pass-through adds no whole-file transfer delay (FR-014a).

**Constraints**: Zero project-attributable cost (FR-007, FR-008); no direct Internet-facing application or management listener (FR-003) — The narrowly scoped WireGuard UDP transport listener defined by the Option A compute-link contract (C1a) is explicitly excluded from this prohibition. — with that listener's scope verified under SC-018 and its direct UDP reachability a hard Option A precondition (FR-041); origin holds no job state (FR-014); GPU concurrency remains one (FR-021); 10 MiB uploads and 24-hour retention unchanged (FR-019, FR-028); interim Quick Tunnel testing capped at 200 concurrent requests and no SSE (FR-012b).

**Scale/Scope**: Single origin, single GPU laptop, one serial queue. Realistic load is far below the 5 GB/day zrok fallback quota and the Cloudflare free-plan boundary.

## Constitution Check

*GATE: evaluated against constitution v1.2.0 before Phase 0 and re-checked after Phase 1.*

| Principle | Status | Notes |
|---|---|---|
| I. Smallest Verified Vertical Slice | **PASS** | Deployment-layer slice only. No payment, Kubernetes, Redis, cloud GPU, or object storage introduced. |
| II. Evidence-Gated Completion | **PASS** | Every hardware-, network-, and reboot-dependent claim is operator-executed with captured evidence. Origin OS stays `PENDING` rather than assumed. |
| III. Security and Private-Service Boundary | **PASS, one precondition** | The public application has no direct Internet-facing application or management listener. The only inbound socket permitted by the clarified contract is the authenticated, firewall-scoped WireGuard transport listener; it exposes no application or management service, its scope is verified under SC-018, and Option A itself is void if that transport is not directly receivable without router forwarding (FR-041). Capability-token policy (b) is unchanged. TLS-terminating third party is disclosed per FR-018, now provider-scoped so the disclosure stays accurate if zrok carries traffic. |
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
├── wireguard/                    # REVISED — addressing unchanged; origin transport boundary now in scope (C1a)
│   ├── edge.conf.example
│   ├── upstream.conf.example
│   └── origin-transport-boundary.md   # NEW — OS-independent transport-boundary definition (SC-018)
├── firewall/origin/              # NEW — provisional per-OS transport-boundary rule snippets (research.md R1)
└── windows/services/
    ├── web.xml                   # REVISED — remove 10.10.0.2 bind and WireGuard <depend>
    ├── api.xml                   # verified loopback-bound
    └── comfyui.xml               # verified loopback-bound

scripts/
├── windows/                      # GPU-laptop start/recovery, revised for LAN independence
│   ├── start_web_service.ps1     # REVISED — drop tunnel-address gating
│   └── health_chain.ps1          # NEW — per-layer health probes
└── verify/                       # REVISED + NEW — boundary and acceptance evidence
    ├── test_origin_lockdown.py   # REVISED — no direct Internet-facing application/management listener; the C1a transport port is permitted and never probed as prohibited
    ├── test_egress_identity.py   # NEW — provider-scoped approved-address proof
    ├── test_wireguard_transport_boundary.py  # NEW — static verifier for the C1a boundary (SC-018)
    ├── test_mobility.py          # REUSED — laptop mobility across external networks (FR-040, SC-017)
    └── test_lan_independence.py  # NEW — LAN works with binding down

tests/security/
├── test_caddy_contract.py        # REVISED — loopback-only, streaming, no buffering
├── test_wireguard_transport_boundary.py  # NEW — C1a boundary contract test + negative fixtures (SC-018)
└── test_compute_link_startup.py  # REVISED — startup must not gate on the binding

docs/operations/                  # REVISED runbooks; EU.org/inbound-era content retired
evidence/public-deployment/       # Cutover evidence set, provider-scoped
```

**Structure Decision**: No new application tier. Work concentrates in `deploy/`, `scripts/`, `tests/security/`, `docs/operations/`, and `evidence/`. The only application-adjacent change is removing the private-address binding from the web service so feature 001 starts without WireGuard. `apps/api` additionally enforces FR-031 admission bounds in the existing SQLite acceptance transaction: queue capacity, rolling-minute acceptance rate, and repeated identical inputs. This is the required T057 application exception; no new service or schema is introduced. Existing accepted-job behavior, isolation, adapter, upload/retention/disk limits, and browser journey remain intact.

## Complexity Tracking

> No Constitution Check violations. This section is intentionally empty.

## Implementation terminology (2026-09-06)

The primary component name is **origin pass-through** (Caddy on the approved origin). The **connector** is cloudflared or the cause-gated zrok replacement. The laptop-facing application role is **job service**. Historical feature-002 web-entry/proxy terminology in superseded records does not change these roles.
