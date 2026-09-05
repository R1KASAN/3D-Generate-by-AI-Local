> **Superseded by [feature 003](../003-outbound-tunnel-entry/spec.md).** This artifact preserves feature-002 history; its inbound-proxy, certificate, and tunnel-gated startup instructions are not current deployment instructions. Consult `specs/003-outbound-tunnel-entry/` from the repository root.

---

description: "Task list for 002-cloudflare-public-entry"
---

# Tasks: Cloudflare Public Entry for the 3D Generation Service

**Input**: Design documents from `/specs/002-cloudflare-public-entry/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/)

**Tests**: Test tasks ARE included. Constitution Principle VIII requires tests before implementation for authorization boundaries and result access, and the spec's acceptance criteria (SC-001..SC-015) are verification-driven throughout.

**Task IDs are stable identifiers, not an ordering.** T051–T055 were added after the first `/speckit-analyze` pass to close findings C1, C2, U1 and N1. T056–T058 were added after the owner reaffirmed that the institutionally approved address must remain the production origin and that the project budget is zero. They are placed in the phase and position where they must actually run, so numeric order and execution order diverge from T035 onward. Existing IDs were deliberately left unchanged rather than renumbered: the analysis report, the constitution's Sync Impact Report, and this conversation all reference specific IDs, and renumbering would silently invalidate every one of those references. **Follow the checklist order, not the numbers.**

**Organization**: Tasks are grouped by user story. Because this is a deployment feature, the stories share one physical path — see *Story Independence* under Dependencies for what "independently testable" means here.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- **🔒 GATED**: Cannot start until Phase 2 confirmations are in hand. These touch live infrastructure.

## Path Conventions

Repository root is `C:\Users\MetaHosP\Desktop\3D-Generate-by-AI-Local`. Deployment configuration lives under `deploy/`, verification under `scripts/verify/` and `tests/security/`, operator documentation under `docs/operations/`, and recorded evidence under `evidence/`. **No application source under `apps/` is modified by any task in this feature.**

## Current execution-block ledger (2026-09-05)

The remaining unchecked tasks are intentionally not reported as complete. They
require state or evidence unavailable to this repository session:

- **T008 — BLOCKED:** origin owner access, an approved management service/port/source,
  and a fresh connection before default-deny.
- **T021/T055 — BLOCKED:** owner-authorized Cloudflare account access, domain
  acceptance, model-license/permitted-territory approval, and provider-plan
  logging-control results; the public certificate and DNS cutover are
  externally visible and not reversible.
- **T022–T026 — BLOCKED:** the origin host, Origin CA material, live firewall/Caddy state,
  and a genuinely off-campus vantage point.
- **T035/T036/T038–T040/T049 — BLOCKED:** live origin/laptop operation, external access,
  network moves, reboots, and power-cycle trials.
- **T051/T052/T054 — BLOCKED:** the target laptop plus a second physical-network device
  for applying, verifying, and externally proving the upstream boundary.
- **T041/T047 — BLOCKED:** owner-supplied delegation issuer/account/certificate dates and an
  independent handover reviewer.
- **T057/T058 — BLOCKED:** accepted no-cost hostname/provider billing evidence,
  live provider routing, the approved origin, and an external vantage point.
- **T053 — BLOCKED for acceptance:** a second host on the laptop's physical network to prove the
  pre-boundary refusal baseline; the verifier itself is implemented.

No live infrastructure change was made while these prerequisites were absent.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Capture the operator inputs the design has been waiting on, and create the provider-configuration directory so provider state is version-controlled rather than living only in a web dashboard.

- [X] T001 Record operator inputs — origin OS and version, whether the origin already holds `161.200.90.4`, whether anything currently listens on 443, the registered domain name, and the intended management port and source range — in `evidence/public-deployment/operator-inputs.md`, with the address masked per FR-026
- [X] T002 [P] Create `deploy/cloudflare/dns-records.md` documenting the intended record set and the proxy status of each record, including the explicit statement that no record is created for the tunnel endpoint (research.md R5)
- [X] T003 [P] Create `deploy/cloudflare/origin-cert.README.md` describing Origin CA issuance and installation, the file locations on the origin, and an explicit warning that no key material may be committed
- [X] T004 [P] Create `deploy/firewall/README.md` stating that `specs/002-cloudflare-public-entry/contracts/port-policy.md` is authoritative over every firewall implementation, and that a disagreement between an implementation and that table is an implementation bug

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Governance decisions, the written network permissions, and the failing tests that define correct behaviour before any configuration changes.

**⚠️ CRITICAL**: No user story work may begin until this phase completes. T009–T011 are the test-first gate; T008 is the remaining external confirmation that unblocks every 🔒 GATED task. T007 approval is recorded, but its live application remains gated by T008.

- [X] T005 Update `evidence/public-deployment/owner-gate.md` to record the 2026-09-05 decisions — proxied public entry with `161.200.90.4` retained as origin, and operator control of the provider account — and re-scope the former router-forwarding row to the border-firewall permission set from `contracts/port-policy.md`. The later zero-cost decision replaces paid-domain registration with a no-cost delegation whose issuer and accepted label remain pending.
- [X] T006 Write the network permission request — exactly `443/tcp` from provider ranges and `51820/udp` from any source, with port 80 explicitly *not* requested — into `docs/operations/network-permission-request.md`, citing the 26 ธ.ค. 2567 Electrical Engineering Department memo as the allocation basis (corrected 2026-09-05: that memo carries no reference number — see `evidence/public-deployment/allocation-memo-review.md`)
- [X] T007 Obtain and record written confirmation of both inbound permissions in `evidence/public-deployment/network-permissions.md` (FR-030, SC-009). Per FR-030, discovering a further required permission after this point is a planning defect, not a routine follow-up. The project lead explicitly approved exactly `443/tcp` from Cloudflare ranges and `51820/udp` from any source; live application remains gated by T008 and the origin cutover tasks.
- [ ] T008 Decide the origin management path, prove access from the intended source range while the origin is still open, and record the result in `evidence/public-deployment/management-path.md` — this must happen before any default-deny rule is applied. **BLOCKED:** the path decision is recorded as SSH/TCP 22 via a University VPN or bastion `/32` with console fallback, but the exact CIDR, origin listener, and fresh SSH connection proof are unavailable.
- [X] T009 **Extend** `tests/security/test_caddy_contract.py` — do not replace it. **Preserve the existing `test_no_basic_auth` assertion**, which is what enforces FR-023 and Constitution Principle III's no-site-wide-login clause; dropping it would silently remove a governance control while the suite still appeared green. Then add the new assertions from `contracts/origin-entry.md`: no ACME or `email` directive, no `:80` listener, client-certificate verification present, job-credential header deleted from log output, upstream restricted to the tunnel address, and `161.200.90.3` absent from `deploy/**` and network-applying scripts only (not from `docs/` or `evidence/`). **Confirm the new assertions FAIL against the current Caddyfile, and that the preserved `test_no_basic_auth` still PASSES, before proceeding**
- [X] T010 [P] Create `scripts/verify/test_origin_lockdown.py` asserting that a direct connection to the origin address is refused at TLS handshake rather than returning an application error. **Confirm it fails or errors before the origin is configured**
- [X] T011 [P] Create `scripts/verify/test_dns_disclosure.py` asserting that no published record for the zone resolves to the origin address. **Confirm it fails before the proxied record exists**

**Checkpoint**: Governance recorded, permissions confirmed in writing, management path proven, and three failing tests define the target behaviour.

---

## Phase 3: User Story 1 — External visitor generates a 3D model (Priority: P1) 🎯 MVP

**Goal**: A person outside the university completes upload → generate → preview → download through the public subdomain, with no login, over a valid certificate, while the origin refuses everything that did not come through the proxy.

**Independent Test**: From mobile data or an off-campus host, complete the full journey and byte-compare the downloaded model against the server's copy (SC-001).

### Tests for User Story 1 ⚠️

> Write and confirm failing before the implementation tasks below.

- [X] T012 [P] [US1] Update `scripts/verify/test_https_boundary.py` for the proxied topology — visitor-facing chain validates, HTTP redirects at the provider edge, and the origin hop is validated rather than merely encrypted (FR-002, FR-003a)
- [X] T013 [P] [US1] Update `scripts/verify/test_external_ports.py` to assert port 80 has no listener and no firewall rule, alongside the existing checks that 3000, 8000, 8188, 3389, and 2019 are unreachable (FR-006, FR-008, FR-009, SC-004)
- [X] T014 [P] [US1] Review `scripts/verify/test_public_auth.py` against `contracts/origin-entry.md` C5–C6 and extend it to grep every **project-controlled** log — the origin's access and error logs, and the application's logs on the GPU machine — for a known credential value (SC-006). Provider-side logs are deliberately out of scope: they are not retrievable on the owner's plan, and that gap is recorded as residual exposure by T055 rather than pretended away here

### Implementation for User Story 1

- [X] T015 [US1] Rewrite `deploy/caddy/Caddyfile` per `contracts/origin-entry.md` (FR-006, FR-007, FR-008, FR-014, FR-021) — remove the `email` directive and all automatic certificate management, load the Origin CA certificate and key from file, require and verify the provider client certificate, and delete the `:443, :80` catch-all block in favour of a 443-only host guard
- [X] T016 [US1] Update `deploy/caddy/.env.example` — remove `ACME_EMAIL`, add the Origin CA certificate path, key path, and provider origin-pull CA path, and update the header comment that currently describes the IP-certificate fallback
- [X] T017 [US1] Update `deploy/firewall/configure-public-edge.ps1` — delete the `-EnableHttp` parameter and the `Local3D Edge HTTP (ACME/redirect)` rule entirely, and change the 443 rule's `-RemoteAddress` from `Any` to the provider range list
- [X] T018 [P] [US1] Create `deploy/firewall/cloudflare-ranges.ps1` that fetches the current published ranges and rebuilds the 443 rule, failing closed — leaving the existing rule intact and exiting non-zero if the list cannot be retrieved, never falling back to `Any`
- [X] T019 [US1] Create `deploy/firewall/verify-public-edge.ps1` asserting the state in `contracts/port-policy.md` — 443 scoped to provider ranges, **no** port 80 rule, 51820/udp present, management rule scoped, explicit blocks in place — writing masked results to `evidence/public-deployment/firewall.md`
- [X] T020 [P] [US1] Create `docs/operations/cloudflare-setup.md` covering zone creation, the proxied record, SSL mode Full (strict), Authenticated Origin Pulls, Origin CA issuance, **and the Origin CA renewal procedure with its issue/expiry dates** (FR-003c) — the provider renews the visitor-facing certificate but not this one, and its long validity means the expiry will fall well outside the installer's memory
- [ ] T057 🔒 [US1] Before adopting the published name, record provider-plan and naming evidence in `evidence/public-deployment/cost-boundary.md`, demonstrating zero project-attributable recurring charge and free renewal/delegation of the selected hostname (FR-032, FR-033, SC-017). A paid `.com` registration is a failing result, not an accepted exception. **BLOCKED:** the final no-cost hostname and authorized provider billing view are unavailable.
- [ ] T021 🔒 [US1] Configure the provider per `docs/operations/cloudflare-setup.md` (FR-001, FR-001a, FR-003) and record the resulting configuration in `deploy/cloudflare/dns-records.md`. ⚠️ **Irreversible**: the visitor-facing certificate enters public Certificate Transparency logs and the subdomain becomes permanently discoverable. Confirm owner acceptance before this step. **BLOCKED:** authorized Cloudflare/domain access, accepted no-cost hostname, owner acceptance, and the model-license/permitted-territory gate are unresolved.
- [ ] T055 🔒 [US1] While configuring the provider, set every available control that suppresses request-header or credential logging, then create `evidence/public-deployment/residual-exposure.md` naming the provider, stating that it terminates TLS and therefore processes credentials in cleartext, recording which logging controls existed and how each was set, and checking the result against the four conditions in Constitution Principle III v1.2.0 (FR-011a, FR-011b, SC-006a). **BLOCKED:** provider account access and plan-specific logging-control results are unavailable.
- [ ] T022 🔒 [US1] Install the Origin CA certificate and key on the origin at the paths named in `deploy/caddy/.env.example`, then run `caddy validate` and confirm `tests/security/test_caddy_contract.py` now PASSES. **BLOCKED:** origin host access and real Origin CA material are unavailable.
- [ ] T023 🔒 [US1] Apply the origin boundary with `deploy/firewall/configure-public-edge.ps1`, then open a **new** connection to confirm management access still works before ending the session. **BLOCKED:** T008 and live Edge access are unresolved.
- [ ] T024 🔒 [US1] Start Caddy on the origin and confirm the unavailability notice is served — the GPU laptop is intentionally not yet connected, so this proves `handle_errors` works before it is needed. **BLOCKED:** origin host/Caddy access is unavailable.
- [ ] T025 🔒 [US1] Run the Stage 2 boundary verification from an external vantage point per `quickstart.md` (SC-004, SC-011, SC-012), recording results in `evidence/public-deployment/{tls,ports,dns,origin-lockdown}.md`. **BLOCKED:** live origin state and an authorized off-campus vantage point are unavailable.
- [ ] T026 🔒 [US1] Run the Stage 3 full journey from an external vantage point via `scripts/verify/test_external_acceptance.py` (SC-001, SC-005, FR-015), recording results in `evidence/public-deployment/full-flow.md` and `negative-cases.md`. **BLOCKED:** live provider/origin/laptop path and an authorized off-campus vantage point are unavailable.
- [ ] T058 🔒 [US1] Record a masked provider routing export and external request trace in `evidence/public-deployment/origin-path.md`, proving the application is reached through the single institutionally approved production origin and that no provider-operated tunnel bypasses it (FR-031, SC-016, SC-018). **BLOCKED:** live provider configuration, approved origin access, and an external vantage point are unavailable.

**Checkpoint**: The service is publicly usable from outside the university. This is the MVP.

---

## Phase 4: User Story 2 — GPU machine moves to a different network (Priority: P2)

**Goal**: The laptop relocates between the university, a home network, and a mobile hotspot, and returns from reboot, with no DNS record, proxy configuration, or tunnel address ever edited.

**Independent Test**: Complete the US1 journey with the laptop on three distinct networks and after three consecutive off-campus reboots, with a reviewer confirming nothing was reconfigured between runs (SC-002, SC-003).

**Note**: The compute link was built in the superseded planning round and survives this feature unchanged. Most tasks here are verification against `contracts/compute-link.md` rather than new construction — but they are not skippable, because the contract was written after the code.

### Tests for User Story 2 ⚠️

- [X] T027 [P] [US2] Review `scripts/verify/test_wireguard_reachability.py` against `contracts/compute-link.md` L7 and confirm it contains a **positive** reachability assertion — real peer, fresh handshake, origin reaching the laptop's web entry — not only the negative silent-port check (FR-028)
- [ ] T053 [P] [US2] Create `scripts/verify/test_upstream_lan_lockdown.py` asserting that the GPU laptop's web-entry port is **refused** when contacted from another host on the laptop's own physical LAN or Wi-Fi — proving the binding is enforced by the machine rather than merely hidden by whichever network it currently sits on (FR-009, FR-024, SC-015). **Confirm it FAILS before T051 applies the boundary. BLOCKED:** a second host on the laptop's physical network is unavailable for the required acceptance observation.
- [X] T028 [P] [US2] Review `scripts/verify/test_mobility.py` against `quickstart.md` Stage 4 and confirm it asserts that no configuration file changed between relocations

### Implementation for User Story 2

- [X] T029 [P] [US2] Verify `deploy/wireguard/upstream.conf.example` and `edge.conf.example` against `contracts/compute-link.md` L1–L3 — peer scopes are `/32` on both sides and never `0.0.0.0/0`, keepalive is set on the laptop side only, and the origin peer has **no** `Endpoint` line
- [X] T030 [P] [US2] Verify the laptop tunnel endpoint is the address literal `161.200.90.4:51820` and confirm no DNS record exists for it, since an unproxied tunnel record would publish the origin address and defeat FR-001b (research.md R5)
- [X] T031 [US2] Verify `scripts/windows/start_web_service.ps1` polls for both the tunnel address **and** a live handshake before starting the web entry, and exits non-zero on timeout — a service dependency alone can report started before the interface address exists (`contracts/compute-link.md` L4)
- [X] T032 [US2] Verify `scripts/windows/watchdog_tunnel.ps1` implements the L5 decision tree — diagnose the failing layer before acting, cooldown between attempts at the same layer, and stop-and-escalate after a bounded number of attempts rather than looping
- [X] T033 [P] [US2] Configure the laptop not to suspend while powered, including on lid close, and record the applied `powercfg` settings in `evidence/public-deployment/laptop-power.md` (FR-022)
- [X] T034 [P] [US2] Document the fallback paths for networks that block outbound UDP in `docs/operations/tunnel-setup.md` per `contracts/compute-link.md` L6, prepared in advance rather than discovered during a demonstration
- [ ] T051 [US2] Apply the laptop boundary with `deploy/firewall/configure-upstream-boundary.ps1 -EdgePeer 10.10.0.1 -OwnerApproved`. Without this the web-entry port is left unscoped on the laptop and the 8000/8188/3389 blocks are never installed — the script exists and is correct, it was simply never invoked by any task. **BLOCKED:** the tunnel is absent and no owner-approved rollback path exists for the existing portproxy configuration.
- [ ] T052 [US2] Run `deploy/firewall/verify-upstream-boundary.ps1` and record masked output in `evidence/public-deployment/upstream-boundary.md`, confirming port 3000 is scoped to `10.10.0.1/32` on the tunnel interface and that 8000, 8188, and 3389 are blocked. **BLOCKED:** T051 cannot be applied until the tunnel and safe rollback path exist.
- [ ] T054 🔒 [US2] Run `scripts/verify/test_upstream_lan_lockdown.py` from a second machine on the GPU laptop's **physical** network and record the refusal in `evidence/public-deployment/upstream-boundary.md` (SC-015). Run it at least once on a network the laptop does not own — a hotspot or public Wi-Fi — since that is the case the scoping actually protects against. **BLOCKED:** the second device and required hotspot/public-Wi-Fi observation are unavailable.
- [ ] T035 🔒 [US2] Run the mobility acceptance across at least three distinct networks including one mobile connection, editing nothing, and record results in `evidence/public-deployment/mobility.md`. **BLOCKED:** the live tunnel/laptop and three-network test itinerary are unavailable.
- [ ] T036 🔒 [US2] Run **at least three consecutive** off-campus reboot trials and record each in `evidence/public-deployment/reboot-recovery.md`. Three because the startup-ordering defect this guards against is a race that fails intermittently — one passing run is not evidence. **BLOCKED:** the live tunnel/laptop and off-campus reboot environment are unavailable.

**Checkpoint**: The laptop is genuinely relocatable. The project's central constraint is proven.

---

## Phase 5: User Story 3 — Visitor arrives while the GPU machine is unavailable (Priority: P3)

**Goal**: With the laptop off or disconnected, visitors see a courteous unavailability notice over a valid certificate, and the service restores itself when the laptop returns.

**Independent Test**: Disconnect the laptop, load the subdomain from outside, and confirm a purpose-written notice rather than a raw gateway error (SC-007).

- [X] T037 [P] [US3] Verify (FR-021) that `deploy/caddy/maintenance/maintenance.html` reads as a deliberate service notice rather than an error page, and confirm `handle_errors` in `deploy/caddy/Caddyfile` covers 502, 503, and 504 with a short upstream dial timeout — the laptop being unreachable is routine mobility, not an incident to hang a request on
- [ ] T038 🔒 [US3] With the laptop disconnected, confirm from an external vantage point that the name resolves, the certificate validates, and the notice is served; record in `evidence/public-deployment/degraded-state.md`. **BLOCKED:** the live provider/origin and authorized external vantage point are unavailable.
- [ ] T039 🔒 [US3] Reconnect the laptop and confirm the application is served again within 5 minutes with no operator action (SC-008), recording the observed interval in `evidence/public-deployment/degraded-state.md`. **BLOCKED:** the live provider/origin/laptop path is unavailable.
- [ ] T040 🔒 [US3] Power the laptop off for 30 minutes, restore it, and confirm the tunnel re-establishes unattended — this exercises keepalive and reconnect after a long absence rather than a brief blip — recording in `evidence/public-deployment/degraded-state.md`. **BLOCKED:** the live tunnel/laptop and 30-minute power-cycle environment are unavailable.

**Checkpoint**: All three stories functional. The distinction between *resting* and *broken* is visible to anyone evaluating the project.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T041 [P] Create `docs/operations/naming-continuity.md` recording the no-cost delegation issuer, the provider account identity, delegation review/renewal conditions, **the Origin CA certificate's issue and expiry dates** (FR-003c, SC-014), and the procedure to transfer or reconstruct the naming layer — sufficient for the research programme to restore reachability without the original operator (FR-029, FR-033). **BLOCKED:** owner-supplied issuer/account identity and real delegation/certificate dates are unavailable.
- [X] T042 [P] Rewrite the public-deployment sections of `docs/operations/public-cutover.md` for the proxied topology, replacing the ACME and port-80 steps with Origin CA and provider configuration
- [X] T043 [P] Update the network-boundary sections of `docs/operations/windows-ai-server-runbook.en.md` and `docs/operations/windows-ai-server-runbook.th.md` together — both currently describe home-router port forwarding, which was never correct for a directly-allocated address and is doubly wrong now
- [X] T044 [P] Add a note to `docs/operations/lan-proxy-repair.md` that the stale `172.20.10.6` port proxy is removed permanently and must not be recreated
- [X] T045 [P] Create `docs/operations/external-network-security-checklist.md` entries for the provider-range refresh cadence and the consequence of a stale list — refused legitimate traffic, which is the intended failure direction (research.md R3)
- [X] T046 Review every file under `evidence/public-deployment/` — including `residual-exposure.md` and `upstream-boundary.md` — and confirm each masks network addresses and contains no credential material (SC-010)
- [ ] T047 Conduct the handover review — have someone other than the operator state, from documentation alone, who issues the no-cost name, which account controls the provider, the delegation and Origin CA renewal/review conditions, and how to restore reachability without the operator; record the outcome in `evidence/public-deployment/handover-review.md` (SC-013, SC-014, SC-017). **BLOCKED:** an independent reviewer and real delegation/account/renewal facts are unavailable.
- [X] T048 Run the constitution audit against version **1.2.0** and record it in `evidence/final/constitution-audit.md`, confirming Principle III compliance under both amendments and verifying all four residual-exposure conditions are satisfied and evidenced; note that no exception entry was required because the principle was amended rather than reinterpreted
- [ ] T049 Execute the full `quickstart.md` validation end to end and record the consolidated result in `evidence/final/mvp-acceptance.md`. **BLOCKED:** the complete live provider/Edge/tunnel/laptop path and external test environments are unavailable.
- [X] T050 Mark the superseded public-entry approach as withdrawn in `specs/001-local-3d-generation/tasks.md` (T086–T097), pointing to this feature, so the two task lists do not both appear live
- [X] T056 Reconcile the owner decision across `specs/001-local-3d-generation/tasks.md`, feature 002, feature 003, and `.specify/feature.json`: feature 002 is authoritative, the approved address is the mandatory production origin, feature 003 is superseded, and paid `.com` registration is outside the zero budget

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on T001. **Blocks every user story.** T008 in particular unblocks all 🔒 GATED tasks; T007 approval is recorded but still requires live application during cutover.
- **Phase 3 (US1)**: Depends on Phase 2
- **Phase 4 (US2)**: Depends on Phase 2; its 🔒 tasks additionally depend on T024, since mobility cannot be observed until the public path serves. Within the phase: T053 (failing test) → T051 (apply boundary) → T052 (verify) → T054 (prove refusal from the laptop's own LAN). T051 and T052 are not 🔒 — they touch only the laptop and can run before the public path exists
- **Phase 5 (US3)**: Depends on Phase 2; its 🔒 tasks depend on T024
- **Phase 6 (Polish)**: Documentation tasks (T041–T045 and T056) may run any time after Phase 2; review tasks (T046–T050) depend on all desired stories

### Story Independence — what it means for this feature

These stories share one physical request path, so they are not independently *deployable* the way three application features would be. They are independently *verifiable*, which is the property that matters here:

- **US1** proves the path works at all — the MVP, and the only story that can stand alone
- **US2** proves the path survives the laptop relocating. Requires US1's path to exist, but fails independently of it and is tested by its own procedure
- **US3** proves the path degrades gracefully. Also requires US1's path, and is tested by deliberately breaking the condition US1 depends on

Stopping after US1 yields a working public service that must stay in one place. Stopping after US2 yields the project's actual goal. US3 is presentation quality.

### The one-way doors

| Task | Why it cannot be quietly undone |
|---|---|
| T021 | The visitor-facing certificate enters public Certificate Transparency logs. The subdomain is permanently discoverable from that moment |
| T023 | Applying default-deny without a proven management path can lock the operator out of the origin entirely — which is why T008 is a Phase 2 blocker rather than a step inside T023 |

T055 is placed immediately before T022 rather than in the polish phase because the provider logging controls it records can only be observed while the provider is being configured. Deferring it would mean reconstructing from memory what the dashboard offered.

### Parallel Opportunities

- T002, T003, T004 — different new files, fully parallel
- T010, T011 — different new test files
- T012, T013, T014 — different existing test files
- T018, T020 — a new script and a new document
- T027, T028, T053 — different test files
- T051, T052, T054 are strictly sequential: the verifier asserts the state the configure script produces, and the LAN probe is meaningless until both have run
- T029, T030, T033, T034 — verification of different artifacts
- T041–T045 — five different documents; T056 is the completed cross-spec decision reconciliation

Note that T015, T016, T017, T019 are **not** parallel with each other despite touching different files: T019's verifier asserts the state T017 produces, and T016 supplies the paths T015 reads.

---

## Parallel Example: Phase 2 test-first gate

```bash
# T010 and T011 are new files with no shared dependency:
Task: "Create scripts/verify/test_origin_lockdown.py asserting direct-to-origin is refused at handshake"
Task: "Create scripts/verify/test_dns_disclosure.py asserting no published record resolves to the origin"

# T009 must be confirmed failing before Phase 3 begins:
uv run --project apps/api pytest tests/security/test_caddy_contract.py -v
```

## Parallel Example: User Story 1 tests

```bash
Task: "Update scripts/verify/test_https_boundary.py for the proxied topology"
Task: "Update scripts/verify/test_external_ports.py to assert port 80 is absent"
Task: "Extend scripts/verify/test_public_auth.py to grep project-controlled logs for a credential value"
```

---

## Implementation Strategy

### What can proceed today

Phase 1, and everything in Phase 2 except T008 (management-path proof). All of Phase 3's non-gated tasks — T012 through T020 — can be completed while waiting, which means the entire configuration and verification surface is ready before anyone touches live infrastructure. Phase 6's documentation tasks are also unblocked.

This is deliberate: it keeps the cutover window short, and it means the two one-way doors are opened only after everything that could have been rehearsed has been.

### MVP first

1. Phase 1 → operator inputs captured
2. Phase 2 → governance recorded, permissions confirmed, failing tests written
3. Phase 3 → **STOP and VALIDATE** from an external vantage point
4. The service is publicly usable. Demonstrable at this point

### Incremental delivery

1. Setup + Foundational → ready to cut over
2. US1 → publicly usable, laptop must stay put → **MVP**
3. US2 → laptop relocatable → **the project's actual goal**
4. US3 → graceful degradation → presentation quality
5. Polish → handover-ready

### Sequencing note for a single operator

Phases 4 and 5 could nominally run in parallel with each other, but both require physically moving or powering down the same laptop, so with one operator they serialise regardless. Run Phase 5 first if a demonstration is imminent — the unavailability notice is what a visitor sees when something goes wrong during a demo, and it is far cheaper to verify than the mobility matrix.

---

## Notes

- `[P]` tasks touch different files with no ordering dependency
- 🔒 tasks touch live infrastructure and require the Phase 2 confirmations
- No task in this feature modifies anything under `apps/`
- Every operator action produces a named evidence file; masking is required in all of them (FR-026)
- Commit after each task or logical group
- Stop at any checkpoint to validate independently
