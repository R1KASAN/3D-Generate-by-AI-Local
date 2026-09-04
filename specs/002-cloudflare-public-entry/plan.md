# Implementation Plan: Cloudflare Public Entry for the 3D Generation Service

**Branch**: `002-cloudflare-public-entry` | **Date**: 2026-09-05 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-cloudflare-public-entry/spec.md`

## Summary

Publish the existing 3D generation service at a Cloudflare-proxied subdomain whose origin remains the university-allocated address `161.200.90.4`. The origin keeps running a reverse proxy that forwards to the GPU laptop over an outbound-initiated tunnel, so the laptop stays freely relocatable.

The technical approach turns on three choices, all of which follow from the spec's requirement that the origin be hidden **and** protected rather than merely unadvertised:

1. **Cloudflare Origin CA certificate** on the origin instead of public ACME. The origin certificate no longer needs public trust, which removes public certificate validation entirely — and with it the need to open port 80 at all.
2. **Authenticated Origin Pulls (mTLS)** as the primary control that the origin serves only Cloudflare. IP allowlisting is retained but demoted to defence-in-depth, because an allowlist alone is a weak control that silently degrades whenever the provider's published ranges change.
3. **Cloudflare SSL mode Full (strict)**, so the provider validates the origin certificate rather than accepting whatever is presented.

This is an amendment to work already on disk from the superseded planning round. Most of that work survives; the certificate handling and the inbound port set do not.

## Technical Context

**Language/Version**: PowerShell 5.1 (Windows edge/laptop boundary scripts); Python 3.12 (verification scripts, pytest); Caddy 2 configuration language

**Primary Dependencies**: Caddy 2 (origin reverse proxy); WireGuard (compute link); Cloudflare DNS + proxy + Origin CA + Authenticated Origin Pulls; WinSW v2 (Windows service wrapper, already in use)

**Storage**: No new storage. Existing SQLite job store on the GPU laptop is untouched.

**Testing**: pytest for contract and external-boundary verification (`tests/security/`, `scripts/verify/`); PowerShell verifier scripts for firewall state; manual operator procedures for anything requiring physical relocation

**Target Platform**: Origin — Windows or Linux at `161.200.90.4` (**operator input pending**, see Research R7). GPU laptop — Windows 11 with RTX 5070.

**Project Type**: Deployment/infrastructure change to an existing web service. No application source is modified.

**Performance Goals**: No new latency budget. Generation time dominates by orders of magnitude. The proxy hop adds negligible overhead relative to a multi-minute GPU job; perceived download speed remains bounded by the GPU laptop's current upload bandwidth, which this feature does not address.

**Constraints**:
- Single Internet-facing port (443/tcp). No second public port, per Constitution Principle III.
- Provider request-body limit on the owner's plan is 100 MB — comfortably above the service's 10 MiB policy. Confirmed, not assumed.
- Origin must remain powered and hold the allocated address; it is not relocatable.
- GPU laptop must be relocatable with zero configuration change.
- Compute link must be outbound-initiated from the laptop.

**Scale/Scope**: One origin, one GPU worker, serial job execution. No change to concurrency.

## Constitution Check

*GATE: evaluated before Phase 0 and re-evaluated after Phase 1. Assessed against constitution **v1.2.0**.*

| Principle | Gate | Pre-Phase-0 | Post-Phase-1 |
|---|---|---|---|
| I. Smallest Verified Vertical Slice | Does this add infrastructure beyond the MVP boundary? | **PASS** — publishing the existing service is the final MVP slice; no payment, orchestration, or cloud GPU is introduced | **PASS** |
| II. Evidence-Gated Completion | Is every claim backed by recorded verification? | **PASS** — all acceptance evidence is external-vantage and file-recorded | **PASS** |
| III. Security and Private-Service Boundary | 443 sole entry; internals unreachable; owner-approved access policy; token not written to project-controlled logs | **PASS** — 443 only; port 80 eliminated entirely; per-job token policy permitted since v1.1.0 | **PASS** — origin cryptographically refuses non-provider traffic. The TLS-terminating proxy's cleartext handling of the credential is governed by the v1.2.0 residual-exposure clause: owner-approved, provider logging controls set, exposure evidenced, proxy-to-origin hop encrypted and validated |
| IV. Job and File Isolation | Job credential integrity preserved end to end | **PASS** — credential forwarded unmodified; absent from every project-controlled log | **PASS** — provider handles it in cleartext by design; bounded and evidenced under Principle III v1.2.0 rather than claimed away |
| V. Single-GPU Queue Correctness | Concurrency unchanged | **PASS** — no change to dispatch | **PASS** |
| VI. Replaceable Integration Boundary | Engine details not leaked publicly | **PASS** — engine remains unreachable from the origin | **PASS** |
| VII. Cross-Platform Development Discipline | Platform-specific setup isolated and documented | **CONDITIONAL** — origin OS unknown; risk of two drifting firewall implementations | **PASS** — resolved by making one policy table authoritative over both implementations (R7) |
| VIII. Test-First Critical Behavior | Authorization and boundary behavior tested before implementation | **PASS** — contract test exists and is updated before config changes | **PASS** |
| IX. Ownership-Critical Decisions | Public access control and exposure owner-approved | **PASS** — mode and ownership decided 2026-09-05 | **PASS** — with FR-029 continuity documentation required |
| X. Scope and Simplicity | New component justified | **CONDITIONAL** — adds a third-party provider to the request path | **PASS** — justified in Complexity Tracking |

**Third-party in the request path** is the one genuine addition and is tracked below. No violation requires an exception entry. Principle III was amended twice for this work: v1.1.0 (2026-09-04) covering the no-site-wide-login policy and the private point-to-point link to a non-public compute node, and **v1.2.0 (2026-09-05)** scoping the no-token-logging rule to project-controlled logs and bounding the residual exposure created by a TLS-terminating proxy. The second amendment was made in response to `/speckit-analyze` finding N1 rather than by reinterpreting the principle.

## Project Structure

### Documentation (this feature)

```text
specs/002-cloudflare-public-entry/
├── plan.md              # This file
├── research.md          # Phase 0 — decisions R1..R8
├── data-model.md        # Phase 1 — request path, trust boundaries, state
├── quickstart.md        # Phase 1 — validation guide
├── contracts/
│   ├── origin-entry.md        # What the origin must accept, reject, forward
│   ├── port-policy.md         # Authoritative inbound permission table
│   └── compute-link.md        # Origin ↔ GPU laptop contract
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 — NOT created by /speckit-plan
```

### Source code and configuration (repository root)

Existing files that **change**:

```text
deploy/caddy/Caddyfile                       # ACME → Origin CA; add client_auth (AOP); drop :80 block
deploy/caddy/.env.example                    # ACME_EMAIL out; origin cert/key/AOP CA paths in
deploy/firewall/configure-public-edge.ps1    # remove port 80; scope 443 to provider ranges
tests/security/test_caddy_contract.py        # assert no ACME, assert AOP present, assert no :80
docs/operations/public-cutover.md            # cutover sequence changes
evidence/public-deployment/owner-gate.md     # record mode + ownership decisions
```

Existing files that are **unchanged and still correct**:

```text
deploy/wireguard/edge.conf.example           # compute link survives the change
deploy/wireguard/upstream.conf.example
deploy/firewall/configure-upstream-boundary.ps1
deploy/firewall/verify-upstream-boundary.ps1
deploy/windows/services/web.xml              # tunnel-bound startup chain still correct
scripts/windows/start_web_service.ps1
scripts/windows/watchdog_tunnel.ps1
scripts/verify/test_wireguard_reachability.py
scripts/verify/test_mobility.py
apps/**                                       # no application source is modified
```

New files:

```text
deploy/cloudflare/dns-records.md             # intended record set, proxy status per record
deploy/cloudflare/origin-cert.README.md      # issuance/installation procedure, no key material
deploy/firewall/cloudflare-ranges.ps1        # fetch + apply provider ranges; fail closed
deploy/firewall/verify-public-edge.ps1       # edge verifier (the .ps1 pair was missing one half)
scripts/verify/test_origin_lockdown.py       # direct-to-origin must be refused
scripts/verify/test_dns_disclosure.py        # published DNS must not reveal the origin
scripts/verify/test_upstream_lan_lockdown.py # laptop port 3000 refused from its own LAN
docs/operations/cloudflare-setup.md          # provider-side configuration runbook
docs/operations/naming-continuity.md         # FR-029 — registrar, account, renewal, recovery
docs/operations/network-permission-request.md # the written ask to university network staff
deploy/firewall/README.md                    # declares contracts/port-policy.md authoritative
evidence/public-deployment/operator-inputs.md # origin OS, domain, management path
evidence/public-deployment/residual-exposure.md # FR-011a — what the provider can observe
```

**Structure Decision**: This feature adds no application code. It changes deployment configuration under `deploy/`, verification under `scripts/verify/` and `tests/security/`, and operator documentation under `docs/operations/`. The existing repository layout is retained; `deploy/cloudflare/` is added as a sibling to `deploy/caddy/` so that provider-side configuration is version-controlled as documentation rather than living only in a web dashboard.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| A third-party provider now sits in the request path for all public traffic, including uploaded images and generated models (Principle X) | The owner selected this mode to keep the allocated address as the origin while removing the public certificate burden, narrowing the inbound permission set, and preventing the origin address from being publicly advertised | Serving the origin directly with public ACME was the superseded design. It requires port 80 open to the whole Internet, exposes the origin address to anyone who resolves the name, and places certificate renewal on the operator — a renewal failure while the operator is away takes the service down. |
| Two firewall implementations may be required (PowerShell and nftables) until the origin OS is confirmed (Principle VII) | The origin OS is an operator input not yet reported | Writing only one and deferring the other risks the two drifting once both exist. Mitigated by making `contracts/port-policy.md` authoritative over both, and by having the verifier assert against that table rather than against a hard-coded rule list. |
