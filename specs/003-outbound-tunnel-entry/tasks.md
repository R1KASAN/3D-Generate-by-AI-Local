---

description: "Task list for feature 003 — Zero-Cost Local AI Public Server"
---

# Tasks: Zero-Cost Local AI Public Server

**Input**: Design documents from `/specs/003-outbound-tunnel-entry/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/)

**Tests**: Test tasks ARE included. Constitution VIII requires tests before implementation is considered complete for API contracts, authorization boundaries, upload validation, path isolation, and result access. Where automation is impossible (reboot, interruption, egress, external journey), a manual procedure with captured evidence is the required substitute per Constitution II.

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

- [X] T001 Create `deploy/cloudflared/` directory structure with `services/` subdirectory for provisional per-OS unit definitions
- [X] T002 [P] Write `deploy/cloudflared/config.yml.example` with ingress to the loopback pass-through, no credentials, and a comment block naming the required environment values
- [X] T003 [P] Write `deploy/cloudflared/README.md` covering credential storage outside Git, least-privilege file permissions, and the revocation/replacement procedure per FR-032 and contracts/origin-entry.md O6
- [X] T004 [P] Add `.gitignore` entries for `deploy/cloudflared/*.json`, `deploy/cloudflared/cert.pem`, and any rendered `config.yml` so connector credentials cannot be committed
- [X] T005 [P] Record the origin-OS-unknown constraint in `deploy/cloudflared/services/README.md`, stating that unit definitions stay provisional until physical inspection per research.md R1

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Fix the LAN-only startup deadlock and convert the origin proxy from inbound to loopback. Everything else depends on these.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete. The deadlock fix changes the bindings every later task assumes.

### Tests first

- [X] T006 [P] Extend `tests/security/test_compute_link_startup.py` to assert no feature 001 service declares a WireGuard service dependency and none binds the private address exclusively (FR-023d) — must FAIL before T009/T010
- [X] T007 [P] Extend `tests/security/test_caddy_contract.py` to assert the Caddyfile has no public `:443` listener, no `tls`/`client_auth` block, and no Origin CA or client-CA path references (contracts/origin-entry.md O2) — must FAIL before T011
- [X] T008 [P] Extend `tests/security/test_caddy_contract.py` to assert **absence** of `buffer_requests` and `buffer_responses`, and presence of a body-size guard above 10 MiB (FR-014a, FR-031 request-size element, contracts/origin-entry.md O3) — must FAIL before T011

### Implementation

- [X] T009 Rewrite `deploy/windows/services/web.xml` to bind loopback, remove `-TunnelAddress`/`-EdgeTunnelAddress`/`-WireGuardInterface` arguments, and delete `<depend>WireGuardTunnel$upstream</depend>` per contracts/compute-link.md C4
- [X] T010 Rewrite `scripts/windows/start_web_service.ps1` to start Next.js on `127.0.0.1:3000` unconditionally, removing the tunnel-address and handshake polling that currently gates startup
- [X] T011 Rewrite `deploy/caddy/Caddyfile` for loopback-only listening: delete the `{$PUBLIC_HOSTNAME}` public block's TLS and client-auth config, delete the `:443` host-guard block, keep security headers, log redaction, body guard, streaming defaults, and the `handle_errors` maintenance path
- [X] T012 Update `deploy/caddy/.env.example` to remove `ORIGIN_CERT_PATH`, `ORIGIN_KEY_PATH`, and `ORIGIN_PULL_CA_PATH`, and to document the loopback listen address and the private-binding upstream, confirming the origin retains no operator-managed certificate secret or renewal duty (FR-006, FR-014)
- [X] T013 [P] Verify `deploy/windows/services/api.xml` and `deploy/windows/services/comfyui.xml` bind loopback only and declare no WireGuard dependency; record findings in `evidence/public-deployment/service-bindings.md`
- [X] T014 Add asynchronous bounded-backoff reconnect for the private binding in `scripts/windows/` that never blocks application startup (FR-023d, contracts/compute-link.md C4)
- [X] T015 Confirm the LAN host port forward in `scripts/windows/configure_lan_boundary.ps1` still targets `127.0.0.1:3000` after the binding change, and that the origin reaches the same listener via `10.10.0.2`
- [X] T016 Run T006–T008 and confirm they now PASS

**Checkpoint**: The GPU laptop starts feature 001 without WireGuard, and the origin has no direct Internet-facing application or management listener. The narrowly scoped WireGuard UDP transport listener defined by the Option A compute-link contract (C1a) is explicitly excluded from this prohibition. User story work can begin.

---

## Phase 3: User Story 1 — Generate a 3D Asset from Outside the LAN (Priority: P1) 🎯 MVP

**Goal**: An external visitor completes upload → generation → status → preview → download through a public HTTPS URL, with no client software and no site-wide login.

**Independent Test**: From mobile data with no LAN access, complete the full journey while the AI engine and internal addresses stay directly unreachable.

### Tests for User Story 1

- [X] T017 [P] [US1] Write `scripts/verify/test_lan_independence.py` asserting the LAN journey completes with the origin unreachable and WireGuard stopped (SC-006d, SC-016)
- [X] T018 [P] [US1] Extend `scripts/verify/test_public_auth.py` for missing, wrong, expired, and cross-job tokens returning responses indistinguishable with respect to job existence, confirming feature 001's per-job capability-token model is unchanged (SC-010, FR-016)
- [X] T019 [P] [US1] Extend `scripts/verify/test_external_acceptance.py` with a streaming-only mode asserting no app- or proxy-authored spool or complete-body temp file during maximum-size upload and download (SC-002b)

### Implementation

- [ ] T020 [US1] Install and configure `cloudflared` on the approved origin using `deploy/cloudflared/config.yml.example`, with ingress pointing at the loopback pass-through [MANUAL] [BLOCKED: authorized lab-origin access unavailable; no public management probes]
- [ ] T021 [US1] Create the named tunnel and store its credential outside Git with least-privilege permissions per contracts/origin-entry.md O6 [MANUAL] [BLOCKED: authorized lab-origin access unavailable; no public management probes]
- [ ] T022 [US1] Configure connector auto-start in dependency order with readiness verified before advertising local health (FR-023, contracts/origin-entry.md O7) [MANUAL] [BLOCKED: authorized lab-origin access unavailable; no public management probes]
- [ ] T023 [US1] Establish the interim Quick Tunnel path for external development testing per FR-012b and quickstart.md Stage 3 [MANUAL] [BLOCKED: authorized lab-origin access unavailable; no public management probes]
- [ ] T024 [US1] Verify the full external journey over the Quick Tunnel: upload, generation, status polling, preview, download (SC-001, FR-001) [MANUAL] [BLOCKED: authorized lab-origin access unavailable; no public management probes]
- [ ] T025 [US1] Run T017–T019 and record results in `evidence/public-deployment/external-journey.md` [MANUAL] [BLOCKED: authorized lab-origin access unavailable; no public management probes]
- [X] T026 [US1] Confirm no concurrency or load figures from the Quick Tunnel are recorded as production characteristics, and that the random hostname is never presented as the production identity (FR-012, FR-012b)

**Checkpoint**: The public journey works end-to-end over an interim hostname. Production naming is the only missing piece.

---

## Phase 4: User Story 2 — Start and Recover the Public AI Server (Priority: P2)

**Goal**: Either machine can reboot, in either order, and the public service returns automatically or names the failing layer. Connectivity loss and deliberate public-route disable both behave safely.

**Independent Test**: Reboot each machine three times independently and in both orders, interrupt and restore the origin's Internet connection three times, and deliberately disable the public route.

### Probe decision (must precede the contract test)

- [X] T027 [US2] Decide the GPU/AI-engine layer order per contracts/health-chain.md H2, recording the choice and its probe in `evidence/public-deployment/health-probe-decision.md` (FR-023e) — recommended: adopt the OS-level `nvidia-smi` probe and place GPU above the engine. **This decision is an input to T028**

### Tests for User Story 2

- [X] T028 [P] [US2] Write `tests/security/test_health_chain_contract.py` asserting each layer in contracts/health-chain.md H1 is independently probeable and that no layer reports healthy from a downstream layer it did not verify, using the order chosen in T027 (FR-023c, FR-023e)
- [X] T029 [P] [US2] Extend `scripts/verify/test_wireguard_reachability.py` to assert binding failure degrades the public path only, leaving the LAN workflow operational (FR-023a, SC-006d)

### Implementation

- [X] T030 [US2] Implement `scripts/windows/health_chain.ps1` with one independently callable probe per layer the laptop owns: private binding, job service, AI engine, GPU
- [X] T031 [US2] Implement the origin-side health probes for provider edge and origin/connector layers, in an OS-independent form per research.md R1
- [X] T032 [US2] Implement per-layer recovery per contracts/health-chain.md H4: restart the failed layer first, leave unrelated healthy layers alone, restart a dependent layer only if still unhealthy after its dependency returned plus a grace period, stop after three failures at one layer (FR-024)
- [X] T033 [US2] Implement the project-controlled unavailable response for engine-down, binding-down, and job-service-down, returning within five seconds with no internal address, port, hostname, or stack detail (FR-025, SC-008)
- [X] T034 [US2] Document that a provider error page means origin-down, not application fault, in `docs/operations/windows-ai-server-runbook.en.md` and its Thai counterpart (FR-025a)
- [ ] T035 [US2] Execute the reboot matrix — 3× origin, 3× laptop, and both boot orders with no assumed shared ordering — recording results in `evidence/public-deployment/reboot-matrix.md` (SC-006, SC-006a, SC-006b, FR-023b) [MANUAL] [BLOCKED: authorized lab-origin access unavailable; no public management probes]
- [ ] T036 [US2] Execute the induced-fault matrix from quickstart.md Stage 4, confirming each fault names its own layer (SC-006c) [MANUAL] [BLOCKED: authorized lab-origin access unavailable; no public management probes]
- [ ] T036a [US2] Execute the mobility matrix with `scripts/verify/test_mobility.py`: move the GPU laptop between at least two distinct external networks — for example university or home Wi-Fi and a mobile hotspot — confirm it reconnects and the public journey completes at each location, and confirm that the public DNS record, public hostname, provider tunnel route, approved-origin configuration, feature 001 application configuration, and WireGuard tunnel addressing are all unchanged before and after every move; record in `evidence/public-deployment/mobility.md` (FR-040, SC-017, contracts/compute-link.md C1b). Editing any of those six items to make a scenario pass is a FAIL, not a workaround [MANUAL] [BLOCKED: requires the GPU laptop plus at least two distinct external networks and a live public route]
- [ ] T037 [US2] Verify the public path resumes after the binding returns without restarting the application (SC-006e) [MANUAL] [BLOCKED: authorized lab-origin access unavailable; no public management probes]
- [ ] T038 [US2] Verify origin-powered-down behavior returns the provider error with no direct Internet-facing application or management listener reachable on either machine, and automatic resume (SC-008a, FR-026). The narrowly scoped WireGuard UDP transport listener defined by the Option A compute-link contract (C1a) is explicitly excluded from this prohibition. [MANUAL] [BLOCKED: authorized lab-origin access unavailable; no public management probes]
- [ ] T039 [US2] Execute at least three Internet interruption/restore trials on the approved origin, confirming the connector retries with bounded backoff and the public route recovers within five minutes of connectivity returning in every trial; record in `evidence/public-deployment/interruption-recovery.md` (SC-007, US2-AS2) [MANUAL] [BLOCKED: authorized lab-origin access unavailable; no public management probes]
- [ ] T040 [US2] Deliberately disable the public route through the configuration-independent recovery path, then verify the LAN workflow remains fully usable, existing jobs and generated artifacts are preserved and not deleted, and the origin stays unreachable directly from the Internet; record in `evidence/public-deployment/public-route-disable.md` (FR-038, FR-037, SC-016) [MANUAL] [BLOCKED: authorized lab-origin access unavailable; no public management probes]

**Checkpoint**: Recovery is predictable across reboot, connectivity loss, and deliberate disable, and every failure names its layer.

---

## Phase 5: User Story 3 — Operate with Zero Additional Cost (Priority: P3)

**Goal**: Demonstrate the complete production path costs the project nothing, with no card, paid add-on, or silent paid fallback, and that licences permit the intended public use.

**Independent Test**: Review plan, hostname arrangement, certificate handling, licences, monitoring, and storage; show every introduced dependency is zero-charge.

### Tests for User Story 3

- [X] T041 [P] [US3] Write `scripts/verify/test_cost_boundary.py` asserting every entry in the cost record has zero recurring price, no required payment card, and no enabled paid fallback (SC-005)

### Implementation

- [X] T042 [US3] Record the cost boundary for every introduced dependency in `evidence/public-deployment/cost-boundary.md` per research.md R8, including the removal of the Origin CA certificate and Authenticated Origin Pulls (FR-007, FR-008, FR-009)
- [ ] T043 [US3] Record current Cloudflare free-plan limits, quotas, logging retention, and acceptable-use terms from the operator's own account in `evidence/public-deployment/provider-limits.md` (FR-034) [MANUAL] [BLOCKED: Cloudflare account access — the account that will manage the `mangosgo.com` route; this task needs the provider account, not the lab origin]
- [X] T044 [US3] Record the AI model and workflow licence terms and their compatibility with the intended public audience and use in `evidence/public-deployment/model-licence.md`, stating explicitly that owner risk acceptance is recorded as such and is **not** independent legal verification (FR-035, FR-033) [MANUAL]
- [ ] T045 [US3] Obtain and record written authorization from the `mangosgo.com` owner in `evidence/public-deployment/hostname-authorization.md`, together with the zone's managing Cloudflare account, production-route compatibility, and the continuity path if authorization is withdrawn (FR-010, FR-011, FR-036, SC-014) [MANUAL] [BLOCKED: owner input]
- [ ] T046 [US3] Record the owner-defined degraded-fallback recovery window in `evidence/public-deployment/fallback-policy.md` (FR-011d) [BLOCKED: owner input]
- [X] T047 [US3] Record the zrok fallback's zero-cost status, hostname format, interstitial behavior, and quota in `evidence/public-deployment/fallback-policy.md` (SC-014a)
- [ ] T048 [US3] Record zrok's TLS-termination, logging, and privacy characteristics and obtain owner acceptance separately from Cloudflare's, per contracts/evidence-methods.md E3 (FR-018) [BLOCKED: owner input]
- [ ] T049 [US3] Rehearse the never-authorized case: public release stays blocked, LAN-only remains usable, zrok and Quick Tunnel serve dev/demo only (FR-011d, SC-014b) [MANUAL] [BLOCKED: authorized lab-origin access unavailable; no public management probes]
- [ ] T050 [US3] Rehearse the withdrawn-hostname case: zrok activates as degraded production with cause, start time, and recovery window recorded (FR-011c, FR-011d, SC-014b) [MANUAL] [BLOCKED: authorized lab-origin access unavailable; no public management probes]
- [ ] T051 [US3] Verify during fallback rehearsal that the connector runs on the approved origin, that a tagged external request is correlated on that origin before the job service handles it, and that direct probes of the GPU laptop still receive no project application response (SC-014c, SC-014d, FR-011e) [MANUAL] [BLOCKED: authorized lab-origin access unavailable; no public management probes]
- [ ] T052 [US3] Verify during fallback rehearsal that the residual-exposure record names zrok and no statement still attributes TLS termination solely to Cloudflare (SC-014e) [MANUAL] [BLOCKED: authorized lab-origin access unavailable; no public management probes]

**Checkpoint**: Zero cost is evidenced, licences are recorded, and both fallback causes are rehearsed.

---

## Phase 6: User Story 4 — Preserve the Approved Origin and Private AI Boundary (Priority: P4)

**Goal**: Prove every public request reaches the approved origin while direct access to origin services, GPU workflow, database, artifacts, and administration stays blocked, and that submission abuse is bounded.

**Independent Test**: From outside the LAN, trace a tagged request through the public route to its origin record, then confirm every internal interface refuses or times out.

### Tests for User Story 4

- [X] T053 [P] [US4] Write `scripts/verify/test_egress_identity.py` with a `--provider` switch implementing both methods in contracts/evidence-methods.md E1: Cloudflare connections interface, and zrok connector-locality plus origin egress check
- [X] T054 [P] [US4] **Reopened and re-closed 2026-09-06** — the earlier pass predated the Option A clarification and could not distinguish the permitted transport listener from a violation. Revise `scripts/verify/test_origin_lockdown.py` so that: the permitted WireGuard UDP transport port is accepted and is never probed as a prohibited port; every application and management listener is still rejected; and any probe outcome the script cannot classify unambiguously **fails closed** rather than passing by omission. The remote vantage point cannot prove the transport listener's scope, so the script must say so explicitly and defer that to T066a instead of implying full lockdown. Add `tests/security/test_origin_lockdown_contract.py` as the locally executable validation of that classification. **Re-closed on the revised verifier: `pytest tests/security/ -q` → 74 passed, 1 skipped, including 30 new classification tests.** Live-origin evidence remains separate and blocked (T062, T066a) (FR-003, FR-004, contracts/compute-link.md C1a)
- [X] T055 [P] [US4] Extend `scripts/verify/test_dns_disclosure.py` to assert no `A` record resolves to the approved origin address and DNS returns only provider-facing routing (SC-004, FR-005, FR-011b)
- [X] T056 [P] [US4] Extend `tests/security/test_evidence_masking.py` coverage to the new evidence files added in Phases 4–6
- [ ] T056a [P] [US4] Write `tests/security/test_wireguard_transport_boundary.py` asserting the declared feature-003 origin transport boundary satisfies every rule in contracts/compute-link.md C1a-1: bound to the approved origin address only, exactly one explicitly named WireGuard UDP port, the WireGuard transport/service only, registered peer public-key admission, `/32` tunnel scope on both sides, and **no** TCP application listener, **no** SSH/RDP/VNC or other management listener, **no** catch-all inbound rule, **no** router port forwarding, and **no** direct GPU-laptop Internet exposure (FR-003, FR-004, SC-018) — must FAIL before T058a
- [ ] T056b [P] [US4] Add the negative fixtures to `tests/security/test_wireguard_transport_boundary.py`: synthetic boundary declarations that add an unrelated inbound listener, widen the peer scope beyond `/32`, add a catch-all inbound rule, or introduce a router port forward MUST each be rejected by the same verifier, proving it is not passing vacuously (SC-018, contracts/compute-link.md C1a-1) — must FAIL before T058b

### Implementation

- [X] T057 [US4] Implement submission bounds beyond request size: a bounded queue length, a retry-frequency limit, and a control for abusive repeated submissions, using only zero-cost controls available in the selected path; preserve the existing request-size guard from T008 (FR-031)
- [X] T058 [US4] Verify the T057 bounds under test — oversized queue, rapid retries, and repeated identical submissions are refused safely without affecting accepted in-flight jobs (FR-031, FR-021)
- [ ] T058a [US4] Declare the feature-003 origin WireGuard transport boundary, OS-independently, in `deploy/wireguard/origin-transport-boundary.md`, with provisional per-OS rule snippets under `deploy/firewall/origin/` marked unconfirmed until inspection. The declaration is the authority the T058b verifier reads; it replaces the feature-002 assumption that the WireGuard firewall posture carries forward unchanged (contracts/compute-link.md C1a-1, research.md R1/R10, FR-003, FR-004)
- [ ] T058b [US4] Implement `scripts/verify/test_wireguard_transport_boundary.py` as the local/static verifier: read the T058a declaration, report every C1a-1 rule as an individual check, **fail closed** on any rule it cannot evaluate, and write `evidence/public-deployment/wireguard-transport-boundary.md` (SC-018)
- [ ] T058c [US4] Run T056a–T056b and confirm they now PASS
- [X] T059 [US4] Implement tagged-request correlation on the approved origin that records the request without its capability token or uploaded content (SC-002, FR-002, FR-027)
- [ ] T060 [US4] Verify capability tokens appear in zero project-controlled connector, pass-through, application, and diagnostic logs (SC-009, FR-017) [MANUAL] [BLOCKED: authorized lab-origin access unavailable; no public management probes]
- [ ] T061 [US4] Verify cache-control prevents job data and artifacts being stored in shared edge caches (FR-030) [MANUAL] [BLOCKED: provider account/origin access unavailable; local no-store configuration is implemented and tested]
- [ ] T062 [US4] Verify direct probes to origin pass-through, job service, AI engine, database, storage, metrics, and administration interfaces return no project application response (SC-003, FR-004, FR-015) [MANUAL] [BLOCKED: authorized lab-origin access unavailable; no public management probes]
- [ ] T063 [US4] Verify the GPU laptop is unreachable from the Internet while retaining feature 001's trusted LAN bindings, per contracts/compute-link.md C7 [MANUAL] [BLOCKED: authorized lab-origin access unavailable; no public management probes]
- [ ] T064 [US4] Capture Cloudflare origin-path evidence showing the active connector reports the approved origin address (SC-002a, FR-002a) [MANUAL] [BLOCKED: physical access] [BLOCKED: authorized lab-origin access unavailable; no public management probes]
- [ ] T065 [US4] Record the origin's OS, version, and outbound egress address in `evidence/public-deployment/operator-inputs.md`, replacing the `PENDING TARGET INSPECTION` rows, and confirm whether the approved address is still on a separate machine from the GPU — a finding that it has moved would require re-evidencing before cutover under FR-013 [MANUAL] [BLOCKED: physical access] [BLOCKED: authorized lab-origin access unavailable; no public management probes]
- [ ] T066 [US4] Determine whether `161.200.90.4` is directly bindable on the origin and record the finding; do **not** enable source-address binding without it (FR-002a, contracts/evidence-methods.md E2) [MANUAL] [BLOCKED: physical access] [BLOCKED: authorized lab-origin access unavailable; no public management probes]
- [ ] T066a [US4] Capture origin-local evidence that the **running** origin firewall and WireGuard configuration match the T058a declaration — exactly one WireGuard UDP port on the approved origin address, WireGuard service only, peer-key admission, `/32` scope, and no TCP application listener, management listener, catch-all rule, or router port forward — and record it in `evidence/public-deployment/wireguard-transport-boundary-live.md`. Remote probing cannot substitute for this: an unauthenticated UDP probe of a WireGuard listener is silent, so scope is provable only from the origin itself (SC-018, contracts/compute-link.md C1a-1) [MANUAL] [BLOCKED: authorized lab-origin access unavailable; no public management probes]
- [ ] T066b [US4] Determine, on the approved origin's own network path, whether the origin **directly receives** the selected WireGuard UDP transport without router port forwarding. Record the finding in `evidence/public-deployment/transport-reachability.md`. If it does not, record Option A as **not feasible for this target**, keep production blocked, and open a compute-link transport redesign on a separate outbound-initiated or NAT-traversing arrangement. Do **not** enable router port forwarding, a public application port, a public GPU-laptop listener, or a paid relay or VPS as a workaround (FR-041, contracts/compute-link.md C1c, research.md R9) [MANUAL] [BLOCKED: physical access] [BLOCKED: authorized lab-origin access unavailable; no public management probes]
- [ ] T067 [US4] Verify connector credential revocation stops traffic and its replacement restores the same hostname without exposing any direct Internet-facing application or management listener (SC-013, FR-032). The narrowly scoped WireGuard UDP transport listener defined by the Option A compute-link contract (C1a) is explicitly excluded from this prohibition. [MANUAL] [BLOCKED: authorized lab-origin access unavailable; no public management probes]
- [ ] T068 [US4] Verify five simultaneous submissions execute at most one GPU job at a time with each job isolated (SC-011, FR-020, FR-021) [MANUAL] [BLOCKED: authorized lab-origin access unavailable; no public management probes]
- [ ] T069 [US4] Verify unsupported, corrupt, disguised, and oversized uploads are rejected before GPU execution (SC-012, FR-019) [MANUAL] [BLOCKED: authorized lab-origin access unavailable; no public management probes]
- [ ] T070 [US4] Verify no incomplete artifact is returned as completed under process termination, missing output, low disk, and restart, and confirm feature 001's 24-hour retention and cleanup of uploads, temporary files, job metadata, and artifacts still runs unchanged after the deployment change (SC-015, FR-022, FR-028) [MANUAL] [BLOCKED: authorized lab-origin access unavailable; no public management probes]
- [ ] T071 [US4] Verify new jobs are rejected safely below 10% free disk while active jobs are allowed to reach a safe terminal state where possible, and that the rejection reveals no internal path (FR-029) [MANUAL] [BLOCKED: authorized lab-origin access unavailable; no public management probes]

**Checkpoint**: The boundary is proven in both directions, submissions are bounded, and the approved address is demonstrably in the path.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Retire obsolete feature 002 content, refresh stale evidence, and close the cutover gate

- [X] T072 [P] Update `docs/operations/tunnel-setup.md` for the outbound connector, removing inbound-proxy, Origin CA, and Authenticated Origin Pulls instructions
- [X] T073 [P] Update `docs/operations/public-cutover.md` to the complete FR-033 gate list including licence verification, marking cutover as the only work blocked by hostname authorization
- [X] T074 [P] Update `docs/operations/windows-ai-server-runbook.en.md` and `docs/operations/windows-ai-server-runbook.th.md` for two-machine startup, layered health, and the LAN-independence change
- [X] T075 [P] Update `docs/operations/external-network-security-checklist.md` to reflect that no inbound application or management port exists; the only permitted inbound socket is the C1a WireGuard transport listener
- [X] T076 [P] Retire or annotate `deploy/cloudflare/origin-cert.README.md` and `deploy/firewall/` inbound-era rules that the outbound design makes obsolete
- [X] T077 [P] Update `specs/002-cloudflare-public-entry/` artifacts with a superseded notice pointing to feature 003, without rewriting their history
- [X] T078 Update `evidence/final/constitution-audit.md` so its Principle III row no longer describes the removed "443-only, provider-scoped, mTLS-protected" architecture, and instead records the outbound-only posture and the spec's constitution-alignment note (FR-039 claim limits included)
- [X] T079 Reconcile origin-side component terminology across `spec.md`, `plan.md`, `contracts/`, `tasks.md`, `docs/operations/`, and `deploy/`: choose one primary term for the origin-side component and apply it consistently; the laptop-side listener remains the "job service" (contracts/compute-link.md C6)
- [ ] T080 Run the full `quickstart.md` Stages 1–4 and record consolidated results in `evidence/public-deployment/evidence-review.md` [MANUAL] [BLOCKED: authorized lab-origin access unavailable; no public management probes]
- [ ] T081 Create the production hostname route in the Cloudflare account managing `mangosgo.com` (FR-011a) [MANUAL] [BLOCKED: T045] [BLOCKED: authorized lab-origin access unavailable; no public management probes]
- [ ] T082 Execute `quickstart.md` Stage 5 cutover verification and record the complete evidence set per contracts/evidence-methods.md E6 [MANUAL] [BLOCKED: T081] [BLOCKED: authorized lab-origin access unavailable; no public management probes]
- [ ] T083 Confirm every FR-033 gate item — including licence verification from T044, the SC-018 transport-boundary evidence from T058b and T066a, and the FR-041 direct-UDP-reachability precondition from T066b — is evidenced before enabling production traffic [BLOCKED: T082] [MANUAL] [BLOCKED: authorized lab-origin access unavailable; no public management probes]

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — **BLOCKS all user stories**
- **User Stories (Phases 3–6)**: All depend on Foundational
  - US1 (P1) is the MVP and should complete first
  - US2, US3, US4 can then proceed in parallel or in priority order
- **Polish (Phase 7)**: Depends on the desired stories being complete

### Intra-phase ordering constraints

| Constraint | Reason |
|---|---|
| T027 **before** T028 | The health-chain contract test must assert the layer order chosen by the probe decision (FR-023e) |
| T006–T008 **before** T009–T012 | Tests must fail first (Constitution VIII) |
| T008 **before** T057 | T057 adds queue/retry/abuse bounds on top of the request-size guard |
| T044 **before** T083 | Licence verification is now an FR-033 gate item |
| T056a **before** T058a | The boundary contract test must fail before the boundary declaration exists (Constitution VIII) |
| T056b **before** T058b | The negative fixtures must exist before the verifier they constrain |
| T058a → T058b → T058c | Declaration, verifier, then confirm the two tests pass |
| T058a **before** T066a | Live evidence is compared against the declared boundary, not against an assumption |
| T066b **before** T081 | FR-041 is a feasibility gate: if the origin cannot directly receive the WireGuard UDP transport, Option A is void and cutover must not proceed |
| T045 → T081 → T082 → T083 | Authorization, route creation, cutover verification, gate confirmation |

### User Story Dependencies

- **US1 (P1)**: Depends only on Foundational. No dependency on other stories.
- **US2 (P2)**: Depends on Foundational. Independently testable; US1's connector makes the public-layer probes and interruption trials more meaningful but is not required for the laptop-side layers.
- **US3 (P3)**: Depends on Foundational. Cost and licence evidence are independent; fallback rehearsals benefit from US1 being live.
- **US4 (P4)**: Depends on Foundational. Boundary proofs and submission bounds are independent; origin-path evidence requires US1's connector.

### Blocked and manual task register

Rebuilt from the current task annotations on 2026-09-06. Counts below are derived from the task body, not carried over from an earlier revision.

**Totals**: 40 tasks carry a `[MANUAL]` or `[BLOCKED]` annotation. 39 are still open and blocked; 1 (**T044**, licence research) is `[MANUAL]` and already complete. Phases 1 and 2 contain none.

| Phase / story | Total tasks | Blocked & open | Complete |
|---|---|---|---|
| Phase 1 — Setup | 5 | 0 | 5 |
| Phase 2 — Foundational | 11 | 0 | 11 |
| Phase 3 — US1 | 10 | 6 | 4 |
| Phase 4 — US2 | 15 | 7 | 8 |
| Phase 5 — US3 | 12 | 8 | 4 |
| Phase 6 — US4 | 26 | 14 | 7 |
| Phase 7 — Polish | 12 | 4 | 8 |

Across all phases: **91 tasks, 47 complete, 39 blocked and open, 5 open but locally actionable** (T056a, T056b, T058a, T058b, T058c — the new WireGuard transport-boundary chain). The earlier claim that "no more than four tasks in any user story phase is blocked" was stale and is removed: US4 alone has 14. FR-012a is still satisfied — every blocked item is live-target verification or an external approval, and no local implementation task waits on any of them.

#### Blocker classes

| Class | Exact prerequisite | Tasks |
|---|---|---|
| **A — Lab-origin access** | Authorized physical or remote administrative access to the approved origin. The approved public address alone is not a management endpoint, and no public management probing is permitted. | T020–T025, T035–T040 (except T036a), T049–T052, T060, T062, T063, T066a, T067–T071, T080–T083 |
| **B — Physical origin inspection** | Class A **plus** hands-on inspection of the lab server hardware and its network path | T064, T065, T066, T066b |
| **C — Owner input** | A written decision or authorization from the project owner or the `mangosgo.com` owner | T045, T046, T048 |
| **D — Provider account** | Sign-in to the Cloudflare account that will manage the `mangosgo.com` route | T043, T061 |
| **E — Mobility hardware/networks** | The GPU laptop, at least two distinct external networks, and a live public route | T036a |

#### Register

| Task | Phase / story | Class | Exact prerequisite | Operator action required later | Expected evidence / output |
|---|---|---|---|---|---|
| T020 | P3 / US1 | A | Administrative shell on the approved origin | Install and configure `cloudflared` from `deploy/cloudflared/config.yml.example` | Installed connector with loopback ingress; note in `evidence/public-deployment/external-journey.md` |
| T021 | P3 / US1 | A | Administrative shell on the approved origin | Create the named tunnel; store its credential outside Git with least-privilege permissions | Credential path and permission mode recorded, secret value never committed (O6) |
| T022 | P3 / US1 | A | Class A + origin OS known (T065) | Configure connector auto-start with readiness verified before advertising health | Service/unit definition plus a readiness-before-health transcript (FR-023, O7) |
| T023 | P3 / US1 | A | Class A + outbound Internet from the origin | Establish the interim Quick Tunnel path | Quick Tunnel hostname recorded as development-only, never as production identity (FR-012) |
| T024 | P3 / US1 | A | T023 | Complete upload → generation → status → preview → download over the Quick Tunnel | Full-journey transcript (SC-001, FR-001) |
| T025 | P3 / US1 | A | T017–T019 runnable against a live path | Run the three US1 verifiers against the live path | `evidence/public-deployment/external-journey.md` |
| T035 | P4 / US2 | A | Class A + ability to power-cycle both machines | Run 3× origin reboot, 3× laptop reboot, and both boot orders | `evidence/public-deployment/reboot-matrix.md` (SC-006, SC-006a, SC-006b) |
| T036 | P4 / US2 | A | Class A + a live health chain | Induce a single fault at each layer in turn | Per-layer fault transcript naming each layer (SC-006c) |
| T036a | P4 / US2 | **E** | GPU laptop + ≥2 distinct external networks + live public route | Physically move the laptop between networks and re-run the journey at each | `evidence/public-deployment/mobility.md` with before/after configuration snapshots proving the six protected items are unchanged (FR-040, SC-017) |
| T037 | P4 / US2 | A | Class A + ability to drop and restore the binding | Drop the binding, restore it, confirm no application restart is needed | Resume transcript (SC-006e) |
| T038 | P4 / US2 | A | Class A + ability to power down the origin | Power the origin down; probe from outside | Provider-error transcript plus a listener probe showing no Internet-facing application or management listener (SC-008a) |
| T039 | P4 / US2 | A | Class A + control of the origin's Internet link | Interrupt and restore connectivity at least three times | `evidence/public-deployment/interruption-recovery.md` (SC-007) |
| T040 | P4 / US2 | A | Class A | Disable the public route through the configuration-independent path | `evidence/public-deployment/public-route-disable.md` showing jobs and artifacts preserved (FR-037, FR-038, SC-016) |
| T043 | P5 / US3 | **D** | Sign-in to the Cloudflare account that will manage the route | Read and transcribe the account's current limits, quotas, retention, and AUP | `evidence/public-deployment/provider-limits.md` (FR-034) |
| T045 | P5 / US3 | C | A written reply from the `mangosgo.com` owner | Request authorization personally; the project must not do this on the operator's behalf (FR-036) | `evidence/public-deployment/hostname-authorization.md` (FR-010, FR-011) |
| T046 | P5 / US3 | C | A recovery-window value from the project owner | Record the owner's actual figure; no default may be inferred | Recovery-window block in `evidence/public-deployment/fallback-policy.md` (FR-011d) |
| T048 | P5 / US3 | C | Written owner acceptance of zrok's residual TLS exposure, separate from Cloudflare's | Record acceptance and verify whether zrok exposes a logging-suppression control | zrok section of `evidence/public-deployment/fallback-policy.md` (FR-018, E3) |
| T049 | P5 / US3 | A | Class A + a stageable rehearsal | Rehearse the never-authorized case | Rehearsal record showing release blocked and LAN-only usable (SC-014b) |
| T050 | P5 / US3 | A | Class A + T046, T048 | Rehearse the withdrawn-hostname case | Degraded-production record with cause, start time, and recovery window (SC-014b) |
| T051 | P5 / US3 | A | T050 in progress | Run `test_egress_identity.py --provider zrok` from the origin | Connector-locality and egress evidence (SC-014d, FR-011e) |
| T052 | P5 / US3 | A | T050 in progress | Confirm the residual-exposure record names zrok for that period | Updated residual-exposure record (SC-014e) |
| T060 | P6 / US4 | A | Class A + access to connector, pass-through, and application logs | Search every project-controlled log for a known test token | Zero-match search transcript (SC-009, FR-017) |
| T061 | P6 / US4 | **D** | Cloudflare account access to read the effective cache policy | Confirm the provider does not store job data or artifacts in a shared cache | Cache-policy evidence; local `no-store` configuration is already implemented and tested (FR-030) |
| T062 | P6 / US4 | A | Class A + an off-LAN vantage point | Probe every documented application, AI, database, metrics, and administration interface | Probe transcript showing no project application response (SC-003, FR-004) |
| T063 | P6 / US4 | A | Class A + an off-LAN vantage point | Probe the GPU laptop from the Internet; confirm LAN bindings still work | Boundary transcript (contracts/compute-link.md C7) |
| T064 | P6 / US4 | B | Class A + a live Cloudflare tunnel | Run `test_egress_identity.py --provider cloudflare` | Connections-interface record showing the approved origin address (SC-002a, FR-002a) |
| T065 | P6 / US4 | B | Hands-on inspection of the lab server | Record the origin's OS, version, and outbound egress address | `evidence/public-deployment/operator-inputs.md` with the `PENDING` rows replaced |
| T066 | P6 / US4 | B | Hands-on inspection of the lab server | Determine whether `161.200.90.4` is directly bindable on the origin | Bindability finding; source-address binding stays disabled unless it passes (E2) |
| T066a | P6 / US4 | A | Class A, and T058a declaring the boundary first | Compare the running firewall and WireGuard configuration against the declaration | `evidence/public-deployment/wireguard-transport-boundary-live.md` (SC-018) |
| T066b | P6 / US4 | B | Inspection on the origin's own network path | Determine whether the origin directly receives the WireGuard UDP transport without router forwarding | `evidence/public-deployment/transport-reachability.md`. **A negative result voids Option A: production stays blocked and the transport is redesigned** (FR-041) |
| T067 | P6 / US4 | A | Class A + a live tunnel | Revoke the active credential, then install its replacement | Revocation/restore transcript with no Internet-facing application or management listener exposed (SC-013) |
| T068 | P6 / US4 | A | Class A + a live public path | Submit five simultaneous jobs through the public route | Concurrency transcript (SC-011). Local API regression already passes; this is the live acceptance |
| T069 | P6 / US4 | A | Class A + a live public path | Submit unsupported, corrupt, disguised, and oversized uploads | Rejection transcript (SC-012). Local API regression already passes |
| T070 | P6 / US4 | A | Class A + a live public path | Terminate mid-job, remove an output, fill the disk, restart | No-incomplete-artifact transcript plus a 24-hour retention run (SC-015, FR-028) |
| T071 | P6 / US4 | A | Class A + ability to drive free disk below 10% | Submit while below the threshold with a job in flight | Rejection transcript revealing no internal path (FR-029) |
| T080 | P7 | A | Class A | Run quickstart Stages 1–4 end to end | `evidence/public-deployment/evidence-review.md` |
| T081 | P7 | A + C | T045 authorization, plus Class D account access, plus T066b passing | Create the production hostname route in the Cloudflare account managing `mangosgo.com` | Route-creation record (FR-011a) |
| T082 | P7 | A + C | T081 | Execute quickstart Stage 5 cutover verification | Complete cutover evidence set (contracts/evidence-methods.md E6) |
| T083 | P7 | A + C | T082 | Confirm every FR-033 gate item is evidenced | Signed gate confirmation covering FR-035 licence, SC-018 boundary, and FR-041 reachability |

### Parallel Opportunities

- Phase 1: T002–T005 all parallel
- Phase 2 tests: T006–T008 parallel; implementation T009/T010 (laptop) and T011/T012 (origin) are different machines and can proceed in parallel
- Phase 3 tests: T017–T019 parallel
- Phase 4 tests: T028–T029 parallel **after** T027; T036a is independent of the reboot matrix and may be scheduled whenever the laptop can travel
- Phase 6 tests: T053–T056 parallel; T056a–T056b parallel with them (different file)
- Phase 7: T072–T077 all parallel

---

## Parallel Example: Phase 2 Foundational

```bash
# Write all three failing contract tests together:
Task: "Extend tests/security/test_compute_link_startup.py for binding independence"
Task: "Extend tests/security/test_caddy_contract.py for no Internet-facing application listener"
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
3. US2 → recovery predictable across reboot, interruption, and deliberate disable
4. US3 → zero cost evidenced, licences recorded, fallback rehearsed
5. US4 → boundary proven, submissions bounded, approved address evidenced
6. Polish → docs and stale evidence refreshed, cutover gate closed when authorization lands

### Recommended First Task

**T006 + T009 + T010** — the `web.xml` deadlock. It is the only item in this plan that breaks an already-working feature 001 capability, and quickstart.md Stage 1 fails until it is fixed.

---

## Notes

- New tasks added by the 2026-09-06 Option A remediation use sub-lettered IDs (`T036a`, `T056a`, `T058a`, `T066a`, …) inserted at their correct execution position. Full renumbering was rejected deliberately: features 001 and 002 reuse the same `T0nn` numbering, and roughly twenty committed evidence and documentation files already cite feature-003 IDs, so renumbering would silently invalidate those references. IDs remain unique and monotonic in execution order.
- `[P]` tasks touch different files with no incomplete dependencies
- `[MANUAL]` tasks need operator execution on target hardware; capture evidence per Constitution II
- `[BLOCKED]` tasks name their blocker; none of them block other work
- FR-023a and FR-023d are deliberately kept separate: one specifies startup behavior, the other binding configuration
- **FR-012a has no task by design.** It is a governance constraint on how this plan is sequenced — implementation must not stall on hostname authorization — and it is discharged by the blocked-task register above showing that no local implementation task waits on an external approval, not by a deliverable
- Do not mark a hardware- or network-dependent task complete on the strength of a checkbox alone
- Commit after each task or logical group

## Remediation checkpoint — 2026-09-06 (Option A consistency pass)

Specification, planning, and task artifacts only, plus the one verifier revision T054 explicitly required. No application code, firewall state, WireGuard runtime configuration, provider configuration, or live infrastructure was touched.

| Item | Resolution |
|---|---|
| Inbound wording | Normalized in FR-033, SC-008a, SC-013, US2 independent test and AS5, T038, T067, the Phase 2 checkpoint, contracts, quickstart, data-model, and the operator runbooks. The application and management boundary is unchanged |
| WireGuard firewall coverage | New SC-018 plus T056a, T056b (tests), T058a, T058b, T058c (configuration and verifier), T066a (live evidence, blocked) |
| Mobility | Promoted to FR-040 and SC-017 with T036a |
| Direct UDP reachability | Hard Option A precondition FR-041, contracts C1c, research R9, task T066b, and an FR-033 gate item |
| T054 | Reopened, verifier revised to classify the permitted transport listener separately and fail closed on ambiguity, re-closed on a passing local contract test |
| Blocked-task register | Rebuilt from the current annotations; the stale "no more than four per story" claim removed |
| `NEEDS CLARIFICATION` | Replaced with `PENDING TARGET INSPECTION` where the gap is missing evidence, cross-referenced to T065/T066/T066a/T066b |
| Lifecycle status | Now "Implementation in progress", not "Ready for planning" |
| Cloudflare dependencies | Three duplicate bullets merged into one authoritative dependency |

## Implementation checkpoint — 2026-09-06

Local code, verifier, proxy, and documentation evidence: `evidence/public-deployment/outbound-implementation.md`. Marked software tasks are validated locally; T061 proves configured no-store behavior, while the actual provider cache policy remains part of T082/FR-033. T068–T071 retain live acceptance despite passing local API regressions. No checkbox represents a physical trial that did not run.

The operator explicitly confirmed no authorized remote connection to the lab origin exists and instructed that all live-origin work remain MANUAL/BLOCKED until authorized physical or remote access is available. The approved public address alone is not a management endpoint. No public management probes are permitted. This checkpoint supersedes the earlier blanket statement that all stages 1–4 are operationally unblocked.

Compute-link transport clarification (2026-09-06): **Option A** is selected. “No inbound” means no Internet-facing application or management listener. The origin may expose only the authenticated, firewall-scoped WireGuard UDP transport listener required by C1; it cannot expose Feature 001, ComfyUI, administration, storage, metrics, or the origin pass-through. This resolves the C1/O1 wording conflict without changing implementation. Hostname authorization, provider-specific zrok exposure acceptance, fallback recovery window, and live firewall evidence remain separate human inputs.

Primary terminology: **origin pass-through** for origin Caddy, **connector** for the provider process, **job service** for the laptop role. Historical feature-002 names remain explicitly historical.
