---

description: "Task list for feature 003 — Zero-Cost Local AI Public Server"
---

# Tasks: Zero-Cost Local AI Public Server

**Input**: Design documents from `/specs/003-outbound-tunnel-entry/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/)

**Tests**: Test tasks ARE included. Constitution VIII requires tests before implementation is considered complete for API contracts, authorization boundaries, upload validation, path isolation, and result access. Where automation is impossible (reboot, egress, external journey), a manual procedure with captured evidence is the required substitute per Constitution II.

**Organization**: Grouped by user story so each is independently implementable and testable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US4)
- **[MANUAL]**: Requires operator execution on target hardware; evidence captured instead of automated assertion
- **[BLOCKED]**: Cannot complete until a named owner input or physical inspection lands

## Path Conventions

Split-host deployment layer over an existing web application. Paths per [plan.md](plan.md) Project Structure: `deploy/`, `scripts/`, `tests/security/`, `docs/operations/`, `evidence/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Scaffolding for the outbound connector, with no behavior change yet

- [ ] T001 Create `deploy/cloudflared/` directory structure with `services/` subdirectory for provisional per-OS unit definitions
- [ ] T002 [P] Write `deploy/cloudflared/config.yml.example` with ingress to the loopback pass-through, no credentials, and a comment block naming the required environment values
- [ ] T003 [P] Write `deploy/cloudflared/README.md` covering credential storage outside Git, least-privilege file permissions, and the revocation/replacement procedure per FR-032 and contracts/origin-entry.md O6
- [ ] T004 [P] Add `.gitignore` entries for `deploy/cloudflared/*.json`, `deploy/cloudflared/cert.pem`, and any rendered `config.yml` so connector credentials cannot be committed
- [ ] T005 [P] Record the origin-OS-unknown constraint in `deploy/cloudflared/services/README.md`, stating that unit definitions stay provisional until physical inspection per research.md R1

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Fix the LAN-only startup deadlock and convert the origin proxy from inbound to loopback. Everything else depends on these.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete. The deadlock fix changes the bindings every later task assumes.

### Tests first

- [ ] T006 [P] Extend `tests/security/test_compute_link_startup.py` to assert no feature 001 service declares a WireGuard service dependency and none binds the private address exclusively (FR-023d) — must FAIL before T009/T010
- [ ] T007 [P] Extend `tests/security/test_caddy_contract.py` to assert the Caddyfile has no public `:443` listener, no `tls`/`client_auth` block, and no Origin CA or client-CA path references (contracts/origin-entry.md O2) — must FAIL before T011
- [ ] T008 [P] Extend `tests/security/test_caddy_contract.py` to assert **absence** of `buffer_requests` and `buffer_responses`, and presence of a body-size guard above 10 MiB (FR-014a, contracts/origin-entry.md O3) — must FAIL before T011

### Implementation

- [ ] T009 Rewrite `deploy/windows/services/web.xml` to bind loopback, remove `-TunnelAddress`/`-EdgeTunnelAddress`/`-WireGuardInterface` arguments, and delete `<depend>WireGuardTunnel$upstream</depend>` per contracts/compute-link.md C4
- [ ] T010 Rewrite `scripts/windows/start_web_service.ps1` to start Next.js on `127.0.0.1:3000` unconditionally, removing the tunnel-address and handshake polling that currently gates startup
- [ ] T011 Rewrite `deploy/caddy/Caddyfile` for loopback-only listening: delete the `{$PUBLIC_HOSTNAME}` public block's TLS and client-auth config, delete the `:443` host-guard block, keep security headers, log redaction, body guard, streaming defaults, and the `handle_errors` maintenance path
- [ ] T012 Update `deploy/caddy/.env.example` to remove `ORIGIN_CERT_PATH`, `ORIGIN_KEY_PATH`, and `ORIGIN_PULL_CA_PATH`, and to document the loopback listen address and the private-binding upstream
- [ ] T013 [P] Verify `deploy/windows/services/api.xml` and `deploy/windows/services/comfyui.xml` bind loopback only and declare no WireGuard dependency; record findings in `evidence/public-deployment/service-bindings.md`
- [ ] T014 Add asynchronous bounded-backoff reconnect for the private binding in `scripts/windows/` that never blocks application startup (FR-023d, contracts/compute-link.md C4)
- [ ] T015 Confirm the LAN host port forward in `scripts/windows/configure_lan_boundary.ps1` still targets `127.0.0.1:3000` after the binding change, and that the origin reaches the same listener via `10.10.0.2`
- [ ] T016 Run T006–T008 and confirm they now PASS

**Checkpoint**: The GPU laptop starts feature 001 without WireGuard, and the origin proxy has no inbound listener. User story work can begin.

---

## Phase 3: User Story 1 — Generate a 3D Asset from Outside the LAN (Priority: P1) 🎯 MVP

**Goal**: An external visitor completes upload → generation → status → preview → download through a public HTTPS URL, with no client software and no site-wide login.

**Independent Test**: From mobile data with no LAN access, complete the full journey while the AI engine and internal addresses stay directly unreachable.

### Tests for User Story 1

- [ ] T017 [P] [US1] Write `scripts/verify/test_lan_independence.py` asserting the LAN journey completes with the origin unreachable and WireGuard stopped (SC-006d, SC-016)
- [ ] T018 [P] [US1] Extend `scripts/verify/test_public_auth.py` for missing, wrong, expired, and cross-job tokens returning responses indistinguishable with respect to job existence (SC-010)
- [ ] T019 [P] [US1] Extend `scripts/verify/test_external_acceptance.py` with a streaming-only mode asserting no app- or proxy-authored spool or complete-body temp file during maximum-size upload and download (SC-002b)

### Implementation

- [ ] T020 [US1] Install and configure `cloudflared` on the approved origin using `deploy/cloudflared/config.yml.example`, with ingress pointing at the loopback pass-through [MANUAL]
- [ ] T021 [US1] Create the named tunnel and store its credential outside Git with least-privilege permissions per contracts/origin-entry.md O6 [MANUAL]
- [ ] T022 [US1] Configure connector auto-start in dependency order with readiness verified before advertising local health (FR-023, contracts/origin-entry.md O7) [MANUAL]
- [ ] T023 [US1] Establish the interim Quick Tunnel path for external development testing per FR-012b and quickstart.md Stage 3 [MANUAL]
- [ ] T024 [US1] Verify the full external journey over the Quick Tunnel: upload, generation, status polling, preview, download (SC-001) [MANUAL]
- [ ] T025 [US1] Run T017–T019 and record results in `evidence/public-deployment/external-journey.md`
- [ ] T026 [US1] Confirm no concurrency or load figures from the Quick Tunnel are recorded as production characteristics (FR-012b)

**Checkpoint**: The public journey works end-to-end over an interim hostname. Production naming is the only missing piece.

---

## Phase 4: User Story 2 — Start and Recover the Public AI Server (Priority: P2)

**Goal**: Either machine can reboot, in either order, and the public service returns automatically or names the failing layer.

**Independent Test**: Reboot each machine three times independently and in both orders, then interrupt and restore the origin's Internet connection.

### Tests for User Story 2

- [ ] T027 [P] [US2] Write `tests/security/test_health_chain_contract.py` asserting each layer in contracts/health-chain.md H1 is independently probeable and that no layer reports healthy from a downstream layer it did not verify (FR-023c)
- [ ] T028 [P] [US2] Extend `scripts/verify/test_wireguard_reachability.py` to assert binding failure degrades the public path only, leaving the LAN workflow operational (SC-006d)

### Implementation

- [ ] T029 [US2] Decide the GPU/AI-engine layer order per contracts/health-chain.md H2, recording the choice and its probe in `evidence/public-deployment/health-probe-decision.md` — recommended: adopt the OS-level `nvidia-smi` probe and place GPU above the engine
- [ ] T030 [US2] Implement `scripts/windows/health_chain.ps1` with one independently callable probe per layer the laptop owns: private binding, job service, AI engine, GPU
- [ ] T031 [US2] Implement the origin-side health probes for provider edge and origin/connector layers, in an OS-independent form per research.md R1
- [ ] T032 [US2] Implement per-layer recovery per contracts/health-chain.md H4: restart the failed layer first, leave unrelated healthy layers alone, restart a dependent layer only if still unhealthy after its dependency returned plus a grace period, stop after three failures at one layer
- [ ] T033 [US2] Implement the project-controlled unavailable response for engine-down, binding-down, and job-service-down, returning within five seconds with no internal address, port, hostname, or stack detail (FR-025, SC-008)
- [ ] T034 [US2] Document that a provider error page means origin-down, not application fault, in `docs/operations/windows-ai-server-runbook.en.md` and its Thai counterpart (FR-025a)
- [ ] T035 [US2] Execute the reboot matrix — 3× origin, 3× laptop, both orders — recording results in `evidence/public-deployment/reboot-matrix.md` (SC-006, SC-006a, SC-006b) [MANUAL]
- [ ] T036 [US2] Execute the induced-fault matrix from quickstart.md Stage 4, confirming each fault names its own layer (SC-006c) [MANUAL]
- [ ] T037 [US2] Verify the public path resumes after the binding returns without restarting the application (SC-006e) [MANUAL]
- [ ] T038 [US2] Verify origin-powered-down behavior returns the provider error with no inbound path reachable and automatic resume (SC-008a) [MANUAL]

**Checkpoint**: Recovery is predictable across both machines and every failure names its layer.

---

## Phase 5: User Story 3 — Operate with Zero Additional Cost (Priority: P3)

**Goal**: Demonstrate the complete production path costs the project nothing, with no card, paid add-on, or silent paid fallback.

**Independent Test**: Review plan, hostname arrangement, certificate handling, licenses, monitoring, and storage; show every introduced dependency is zero-charge.

### Tests for User Story 3

- [ ] T039 [P] [US3] Write `scripts/verify/test_cost_boundary.py` asserting every entry in the cost record has zero recurring price, no required payment card, and no enabled paid fallback (SC-005)

### Implementation

- [ ] T040 [US3] Record the cost boundary for every introduced dependency in `evidence/public-deployment/cost-boundary.md` per research.md R8, including the removal of the Origin CA certificate and Authenticated Origin Pulls
- [ ] T041 [US3] Record current Cloudflare free-plan limits, quotas, logging retention, and acceptable-use terms from the operator's own account in `evidence/public-deployment/provider-limits.md` (FR-034) [MANUAL]
- [ ] T042 [US3] Obtain and record written authorization from the `mangosgo.com` owner in `evidence/public-deployment/hostname-authorization.md` (FR-011, FR-036) [MANUAL] [BLOCKED: owner input]
- [ ] T043 [US3] Record the owner-defined degraded-fallback recovery window in `evidence/public-deployment/fallback-policy.md` (FR-011d) [BLOCKED: owner input]
- [ ] T044 [US3] Record the zrok fallback's zero-cost status, hostname format, interstitial behavior, and quota in `evidence/public-deployment/fallback-policy.md` (SC-014a)
- [ ] T045 [US3] Record zrok's TLS-termination, logging, and privacy characteristics and obtain owner acceptance separately from Cloudflare's, per contracts/evidence-methods.md E3 [BLOCKED: owner input]
- [ ] T046 [US3] Rehearse the never-authorized case: public release stays blocked, LAN-only remains usable, zrok and Quick Tunnel serve dev/demo only (SC-014b)
- [ ] T047 [US3] Rehearse the withdrawn-hostname case: zrok activates as degraded production with cause, start time, and recovery window recorded (SC-014b)
- [ ] T048 [US3] Verify during fallback rehearsal that the connector runs on the approved origin and requests traverse it before the laptop (SC-014d, FR-011e)
- [ ] T049 [US3] Verify during fallback rehearsal that the residual-exposure record names zrok and no statement still attributes TLS termination solely to Cloudflare (SC-014e)

**Checkpoint**: Zero cost is evidenced and both fallback causes are rehearsed.

---

## Phase 6: User Story 4 — Preserve the Approved Origin and Private AI Boundary (Priority: P4)

**Goal**: Prove every public request reaches the approved origin while direct access to origin services, GPU workflow, database, artifacts, and administration stays blocked.

**Independent Test**: From outside the LAN, trace a tagged request through the public route to its origin record, then confirm every internal interface refuses or times out.

### Tests for User Story 4

- [ ] T050 [P] [US4] Write `scripts/verify/test_egress_identity.py` with a `--provider` switch implementing both methods in contracts/evidence-methods.md E1: Cloudflare connections interface, and zrok connector-locality plus origin egress check
- [ ] T051 [P] [US4] Rewrite `scripts/verify/test_origin_lockdown.py` to expect **no inbound listener at all** rather than a hardened `:443`, matching the outbound-only design (FR-003, FR-004)
- [ ] T052 [P] [US4] Extend `scripts/verify/test_dns_disclosure.py` to assert no `A` record resolves to the approved origin address and DNS returns only provider-facing routing (SC-004, FR-011b)
- [ ] T053 [P] [US4] Extend `tests/security/test_evidence_masking.py` coverage to the new evidence files added in Phases 4–6

### Implementation

- [ ] T054 [US4] Implement tagged-request correlation on the approved origin that records the request without its capability token or uploaded content (SC-002, FR-027)
- [ ] T055 [US4] Verify capability tokens appear in zero project-controlled connector, pass-through, application, and diagnostic logs (SC-009) [MANUAL]
- [ ] T056 [US4] Verify cache-control prevents job data and artifacts being stored in shared edge caches (FR-030)
- [ ] T057 [US4] Verify direct probes to origin pass-through, job service, AI engine, database, storage, metrics, and administration interfaces return no project application response (SC-003) [MANUAL]
- [ ] T058 [US4] Verify the GPU laptop is unreachable from the Internet while retaining feature 001's trusted LAN bindings, per contracts/compute-link.md C7 [MANUAL]
- [ ] T059 [US4] Capture Cloudflare origin-path evidence showing the active connector reports the approved origin address (SC-002a) [MANUAL] [BLOCKED: physical access]
- [ ] T060 [US4] Record the origin's OS, version, and outbound egress address in `evidence/public-deployment/operator-inputs.md`, replacing the `PENDING` rows [MANUAL] [BLOCKED: physical access]
- [ ] T061 [US4] Determine whether `161.200.90.4` is directly bindable on the origin and record the finding; do **not** enable source-address binding without it (FR-002a, contracts/evidence-methods.md E2) [MANUAL] [BLOCKED: physical access]
- [ ] T062 [US4] Verify connector credential revocation stops traffic and its replacement restores the same hostname without exposing an inbound service (SC-013) [MANUAL]
- [ ] T063 [US4] Verify five simultaneous submissions execute at most one GPU job at a time with each job isolated (SC-011)
- [ ] T064 [US4] Verify unsupported, corrupt, disguised, and oversized uploads are rejected before GPU execution (SC-012)
- [ ] T065 [US4] Verify no incomplete artifact is returned as completed under process termination, missing output, low disk, and restart (SC-015)

**Checkpoint**: The boundary is proven in both directions and the approved address is demonstrably in the path.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Retire obsolete feature 002 content and complete the cutover gate

- [ ] T066 [P] Update `docs/operations/tunnel-setup.md` for the outbound connector, removing inbound-proxy, Origin CA, and Authenticated Origin Pulls instructions
- [ ] T067 [P] Update `docs/operations/public-cutover.md` to the FR-033 gate list, marking cutover as the only work blocked by hostname authorization
- [ ] T068 [P] Update `docs/operations/windows-ai-server-runbook.en.md` and `docs/operations/windows-ai-server-runbook.th.md` for two-machine startup, layered health, and the LAN-independence change
- [ ] T069 [P] Update `docs/operations/external-network-security-checklist.md` to reflect that no inbound port exists rather than a hardened one
- [ ] T070 [P] Retire or annotate `deploy/cloudflare/origin-cert.README.md` and `deploy/firewall/` inbound-era rules that the outbound design makes obsolete
- [ ] T071 [P] Update `specs/002-cloudflare-public-entry/` artifacts with a superseded notice pointing to feature 003, without rewriting their history
- [ ] T072 Reconcile terminology across `docs/` and `deploy/`: the origin-side entry is the "public web entry"; the laptop-side listener is the "job service" (contracts/compute-link.md C6)
- [ ] T073 Run the full `quickstart.md` Stages 1–4 and record consolidated results in `evidence/public-deployment/evidence-review.md`
- [ ] T074 Create the production hostname route in the Cloudflare account managing `mangosgo.com` (FR-011a) [MANUAL] [BLOCKED: T042]
- [ ] T075 Execute `quickstart.md` Stage 5 cutover verification and record the complete evidence set per contracts/evidence-methods.md E6 [MANUAL] [BLOCKED: T074]
- [ ] T076 Confirm every FR-033 gate item is evidenced before enabling production traffic [BLOCKED: T075]

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — **BLOCKS all user stories**
- **User Stories (Phases 3–6)**: All depend on Foundational
  - US1 (P1) is the MVP and should complete first
  - US2, US3, US4 can then proceed in parallel or in priority order
- **Polish (Phase 7)**: Depends on the desired stories being complete

### User Story Dependencies

- **US1 (P1)**: Depends only on Foundational. No dependency on other stories.
- **US2 (P2)**: Depends on Foundational. Independently testable; US1's connector makes the public-layer probes more meaningful but is not required for the laptop-side layers.
- **US3 (P3)**: Depends on Foundational. Cost evidence is independent; fallback rehearsals benefit from US1 being live.
- **US4 (P4)**: Depends on Foundational. Boundary proofs are independent; origin-path evidence requires US1's connector.

### Blocked-task summary

| Blocker | Tasks | Nature |
|---|---|---|
| `mangosgo.com` authorization | T042, T074, T075, T076 | Owner input |
| Degraded-fallback recovery window | T043 | Owner input |
| zrok residual-exposure acceptance | T045 | Owner input |
| Physical origin inspection | T059, T060, T061 | Hardware access |

**Nothing in Phases 1–2, and no more than four tasks in any user story phase, is blocked.** FR-012a is satisfied: implementation proceeds while authorization is outstanding.

### Parallel Opportunities

- Phase 1: T002–T005 all parallel
- Phase 2 tests: T006–T008 parallel; implementation T009/T010 (laptop) and T011/T012 (origin) are different machines and can proceed in parallel
- Phase 3 tests: T017–T019 parallel
- Phase 4 tests: T027–T028 parallel
- Phase 6 tests: T050–T053 parallel
- Phase 7: T066–T071 all parallel

---

## Parallel Example: Phase 2 Foundational

```bash
# Write all three failing contract tests together:
Task: "Extend tests/security/test_compute_link_startup.py for binding independence"
Task: "Extend tests/security/test_caddy_contract.py for no inbound listener"
Task: "Extend tests/security/test_caddy_contract.py for no body buffering"

# Then split by machine:
# Laptop:  T009 web.xml, T010 start_web_service.ps1
# Origin:  T011 Caddyfile, T012 .env.example
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Phase 1 Setup
2. Phase 2 Foundational — **critical**, fixes the deadlock that currently breaks LAN-only operation
3. Phase 3 US1 over the interim Quick Tunnel
4. **STOP and VALIDATE**: full external journey works; LAN still works with WireGuard down
5. Demo-ready without production naming

### Incremental Delivery

1. Setup + Foundational → the LAN regression is fixed and the origin is stateless
2. US1 → external journey works (MVP)
3. US2 → recovery is predictable across both machines
4. US3 → zero cost evidenced, fallback rehearsed
5. US4 → boundary proven, approved address evidenced
6. Polish → docs retired, cutover gate closed when authorization lands

### Recommended First Task

**T006 + T009 + T010** — the `web.xml` deadlock. It is the only item in this plan that breaks an already-working feature 001 capability, and quickstart.md Stage 1 fails until it is fixed.

---

## Notes

- `[P]` tasks touch different files with no incomplete dependencies
- `[MANUAL]` tasks need operator execution on target hardware; capture evidence per Constitution II
- `[BLOCKED]` tasks name their blocker; none of them block other work
- Do not mark a hardware- or network-dependent task complete on the strength of a checkbox alone
- Commit after each task or logical group
