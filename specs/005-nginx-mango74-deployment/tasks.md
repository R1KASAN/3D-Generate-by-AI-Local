# Tasks: NT-Hosted Mango74 Frontend and Stable AI API

**Input**: Design documents in `specs/005-nginx-mango74-deployment/`  
**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`,
`contracts/`, and `quickstart.md`

**Tests**: Required. The constitution and feature specification require
contract, security, failure-path, recovery, browser, and external acceptance
evidence. Test tasks appear before the implementation they govern wherever
dependencies allow.

**Organization**: Tasks are grouped by independently testable user story.
Repository work is separated from administrator-controlled Cloudflare, NT
Server, external-network, and production-runtime gates. A task may be marked
complete only after its stated validation succeeds and sanitized evidence is
recorded.

## Format: `- [ ] T### [P?] [US?] Description with file path`

- **[P]**: Safe to execute in parallel because the task changes a different
  file and has no unmet dependency on another parallel task.
- **[US#]**: Maps the task to the matching user story in `spec.md`.
- Paths are repository-relative and identify the exact implementation or
  evidence target.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Capture the starting state and establish safe configuration,
artifact, and evidence boundaries before production-facing work.

- [X] T001 Capture the current git diff, framework/runtime versions, Windows service states, loopback listeners, portproxy rules, Caddy rollback state, and absence/presence of Nginx/cloudflared without changing them; record only sanitized results in `evidence/feature-005/pre-implementation-baseline.md`
- [X] T002 Extend `.gitignore` to exclude `artifacts/`, Nginx/cloudflared binaries, Tunnel credentials and token-bearing files, service-local secrets, runtime logs, uploads, generated GLBs, models, and production environment files while preserving committed example configuration
- [X] T003 [P] Add the documented static-export, `/mango74` base-path, stable API base URL, and preview-mode variables with non-secret placeholders to `apps/web/.env.example`
- [X] T004 [P] Add the exact production CORS origin, opt-in Firebase preview origin, loopback bindings, adapter, storage, and workflow variables with safe defaults to `apps/api/.env.example`
- [X] T005 [P] Define evidence redaction rules, required UTC timestamps, command/result fields, manual-gate labels, and acceptance file index in `evidence/feature-005/README.md`
- [X] T006 [P] Create a platform-neutral NT Server handoff contract covering static-only contents, `/mango74/` deployment scope, redirect/deep-link behavior, integrity manifest, backup identifier, and rollback inputs in `deploy/nt-server/README.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish shared cross-origin configuration, static export,
Nginx, named-Tunnel, service, packaging, and health foundations used by every
story.

**CRITICAL**: No user-story implementation begins until T007-T029 pass.

### Foundational tests and contracts

- [X] T007 [P] Add an architecture contract that rejects a second application server, direct Notebook ingress, public bindings on ports 3000/8000/8080/8188, production Quick Tunnel references, Caddy as the active production proxy, and committed credential patterns in `tests/security/test_feature005_architecture_contract.py`
- [X] T008 [P] Add a contract test that parses `specs/005-nginx-mango74-deployment/contracts/openapi.yaml`, resolves every internal reference, and verifies the existing `/api/v1` job, cancellation, preview, download, and health operations in `apps/api/tests/contract/test_feature005_openapi.py`
- [X] T009 [P] Add failing settings tests for exact production/preview origins, normalization, duplicate rejection, wildcard refusal, credential refusal, and loopback-only production bindings in `apps/api/tests/unit/test_settings.py`
- [X] T010 [P] Add a failing CORS security matrix for the exact production origin, disabled/enabled Firebase preview origin, HTTP downgrade, look-alike domain, unexpected port, unapproved subdomain, `null`, arbitrary origin, minimal methods/headers, `Vary: Origin`, and disabled credentials in `apps/api/tests/security/test_cors_policy.py`
- [X] T011 [P] Add failing frontend configuration tests for `/mango74`, `https://mango74-api.mangosgo.com/api/v1`, URL joining, absolute resource resolution, trailing slashes, and refusal of local/IP/Quick-Tunnel production values in `apps/web/tests/unit/public-runtime.test.ts`
- [X] T012 [P] Add failing tests proving remembered jobs are scoped by stable API origin, invalid records expire safely, raw job tokens are not logged, and unrelated deployments cannot restore each other's jobs in `apps/web/tests/unit/job-storage.test.ts`
- [X] T013 [P] Add a static Nginx contract test for exact Host acceptance, `/api/` forwarding without destructive rewriting, safe root/unmatched responses, loopback upstream, upload/body limits, timeouts, redacted logs, and absence of public binds in `tests/security/test_nginx_contract.py`
- [X] T014 [P] Add a Windows service contract test for `Local3D-Nginx`, controlled Caddy disable/rollback, loopback startup arguments, deterministic working/log directories, restart policy, and absence of embedded credentials in `tests/security/test_feature005_services_contract.py`
- [X] T015 [P] Add packaging contract tests that accept only deployable static files and reject Backend code, databases, environments, models, workflows, uploads, GLBs, secrets, internal addresses, and `trycloudflare.com` references in `tests/security/test_frontend_package_contract.py`

### Foundational implementation

- [X] T016 Implement validated production CORS and optional Firebase preview settings, strict origin parsing, wildcard/credentials refusal, and loopback-binding validation in `apps/api/src/local3d/config.py`
- [X] T017 Install FastAPI CORS middleware from validated settings with only required methods/headers, credentials disabled, and no effect on job-token authorization in `apps/api/src/local3d/main.py`
- [X] T018 [P] Implement a single browser-safe configuration and URL-resolution module for base path, stable API base, environment validation, and public resource URLs in `apps/web/lib/config/public-runtime.ts`
- [X] T019 [P] Implement API-origin-scoped, expiry-aware remembered-job storage that preserves the job token only in browser storage and provides explicit clear/restore operations in `apps/web/lib/jobs/job-storage.ts`
- [X] T020 Configure production static export, `basePath: '/mango74'`, asset prefix behavior, `trailingSlash: true`, and build-time API validation without changing isolated development/E2E behavior in `apps/web/next.config.ts`
- [X] T021 Implement the production Nginx API-origin configuration on `127.0.0.1:8080`, accepting only `mango74-api.mangosgo.com`, proxying compatible `/api/*` requests to `127.0.0.1:8000`, rejecting root/unmatched Host, and applying approved limits/timeouts/headers/log redaction in `deploy/nginx/nginx.conf`
- [X] T022 [P] Add a generic static Nginx upstream/unavailable response that reveals no upstream address, local path, stack trace, token, or user content in `deploy/nginx/errors/50x.html`
- [X] T023 [P] Add the `Local3D-Nginx` WinSW definition with verified executable/config paths, working/log directories, restart policy, and loopback-only arguments in `deploy/windows/services/nginx.xml`
- [X] T024 Implement a validator that inventories `apps/web/out`, enforces the static-file allowlist, checks `/mango74/` asset references and stable API references, scans forbidden content, and emits a deterministic integrity manifest in `scripts/verify/verify_frontend_package.py`
- [X] T025 Implement a CRLF-safe PowerShell builder that sets approved production variables, runs the static export, invokes the validator, produces `artifacts/front-end.zip` plus SHA-256/manifest, and clears build variables in `scripts/windows/build_frontend_package.ps1`
- [X] T026 [P] Document remotely managed named-Tunnel provisioning, the approved hostname/origin mapping, secure connector-token transfer, Windows service ownership, route rollback, and explicit Quick-Tunnel prohibition in `deploy/cloudflared/named-tunnel.md`
- [X] T027 [P] Implement a credential-free named-Tunnel verifier for service state, process state, public hostname health, origin/CORS response, configuration redaction, and fixed-URL recovery in `scripts/windows/verify_named_tunnel.ps1`
- [X] T028 Extend the health-chain verifier with Nginx Host/path checks, stable public API checks, named-Tunnel state, exact CORS checks, listener/portproxy boundary checks, and a Feature 005 JSON mode without weakening Feature 004 behavior in `scripts/windows/health_chain.ps1`
- [X] T029 Run all Phase 2 unit/contract/security tests, Nginx static validation where a verified binary is available, PowerShell parsing, and a production archive dry run; record exact commands/counts/failures in `evidence/feature-005/foundation-validation.md`

**Checkpoint**: Cross-origin configuration, static export, Nginx, service,
named-Tunnel documentation, packaging, and health foundations are validated.

---

## Phase 3: User Story 1 - Generate a 3D Asset at Mango74 (Priority: P1) 🎯 MVP

**Goal**: A public user loads the static Mango74 frontend, submits one valid
image to the stable API, observes an accurate lifecycle, and previews/downloads
the authorized real GLB produced by the RTX 5070 Notebook.

**Independent Test**: From a genuinely independent network, open
`https://www.mangosgo.com/mango74/`, submit one controlled valid image, observe
queued/running/completed, and verify matching authorized preview/download GLB
hashes while every API request uses only
`https://mango74-api.mangosgo.com/api/v1`.

### Tests for User Story 1

- [X] T030 [P] [US1] Add failing frontend unit tests proving create/status/cancel/preview/download requests and returned relative resource locations resolve against the approved stable API rather than the frontend origin in `apps/web/tests/unit/generation-flow.test.tsx`
- [X] T031 [P] [US1] Add an isolated mock Playwright flow on separate frontend/API test origins that uploads, submits, polls queued/running/completed, previews, downloads, and asserts no real adapter/GPU use in `apps/web/tests/e2e/production-cross-origin.spec.ts`
- [X] T032 [P] [US1] Add a loopback Nginx runtime integration test for exact Host, `/api/v1/health/*`, request body forwarding, response locations, root rejection, unmatched Host rejection, and upstream failure behavior in `tests/security/test_nginx_runtime.py`
- [X] T033 [P] [US1] Add tests for external verifier safety gates, hostname allowlist, independent-network confirmation, token/URL redaction, GLB magic/hash validation, and refusal to probe raw Notebook IPs in `tests/security/test_feature005_external_acceptance_contract.py`

### Implementation for User Story 1

- [X] T034 [US1] Refactor every job operation in `apps/web/lib/api/jobs.ts` to use `public-runtime.ts`, preserve the existing `/api/v1` contract and job-token header, resolve API-relative locations safely, and distinguish HTTP responses from transport failures
- [X] T035 [US1] Update result links, GLB preview source, download behavior, and sanitized public errors to use stable-API resource URLs in `apps/web/components/generation-result.tsx`
- [X] T036 [US1] Update the production UI copy, generation submission flow, base-path-safe navigation, and official/preview environment labels without embedding a hostname or secret in `apps/web/app/page.tsx`
- [X] T037 [US1] Configure Playwright to run the frontend and mock FastAPI on isolated test-only origins/ports with the mock adapter and exact test CORS origin, leaving production port 8000 and runtime configuration unchanged in `apps/web/playwright.config.ts`
- [X] T038 [P] [US1] Implement a guarded external acceptance verifier for frontend assets, stable API requests, lifecycle, authenticated preview/download, hash equality, GLB magic, public-response redaction, and independent-network confirmation in `scripts/verify/test_feature005_external_acceptance.py`
- [X] T039 [US1] Build and validate the production static archive and record archive path, SHA-256, manifest hash, file count, base path, API base, and forbidden-content scan results in `evidence/feature-005/frontend-package.md`
- [X] T040 [US1] Run one isolated mock browser flow through local Nginx and the test API origin, proving cross-origin CORS and all public job operations without using RTX work; record commands and results in `evidence/feature-005/us1-local-mock.md`
- [X] T041 [US1] Run one controlled real Nginx→FastAPI→approved ComfyUI workflow→RTX 5070 generation on loopback only, or reuse evidence only if it proves this exact Nginx route and current workflow revision; record lifecycle, timing, GLB magic/size/hash, and protected preview/download in `evidence/feature-005/us1-local-real.md`
- [ ] T042 [US1] MANUAL GATE: Have the authorized Cloudflare administrator create/approve the named Tunnel and `mango74-api.mangosgo.com` route to `http://127.0.0.1:8080` without exposing a token; record the administrator, change/rollback identifier, hostname, and sanitized verification only in `evidence/feature-005/cloudflare-activation.md`
- [X] T043 [US1] MANUAL GATE: Before changing the NT Server, have its authorized administrator record the product/version, capture the current `/mango74` and representative unrelated-route baseline, and back up the existing `/mango74` state; then deploy only the validated `front-end.zip` and record the release hash, backup/rollback identifier, commands/actions, baseline, and result in `evidence/feature-005/nt-frontend-deployment.md`
- [ ] T044 [US1] MANUAL GATE: From a genuinely independent network run the guarded verifier and one real production job through the NT-hosted frontend and stable named-Tunnel API; record asset, lifecycle, origin, CORS, GLB, redaction, and timing evidence in `evidence/feature-005/us1-external.md`

**Checkpoint**: User Story 1 is independently functional. T041 is the local
MVP; production MVP additionally requires T042-T044.

---

## Phase 4: User Story 2 - Resume and Cancel Work After Refresh (Priority: P2)

**Goal**: An owner can refresh/reopen the frontend, restore the correct job
for the configured API origin, and cancel eligible work without gaining access
to anyone else's job.

**Independent Test**: Submit a queued job, refresh/reopen the page, verify the
same token-authorized job is restored, cancel it, and prove it remains
cancelled; wrong/missing tokens and another browser session remain denied.

### Tests for User Story 2

- [X] T045 [P] [US2] Add failing UI integration tests for restore after refresh, API-origin scoping, expired/malformed storage, terminal-state restoration, and clearing unavailable jobs only after an API-confirmed missing response in `apps/web/tests/unit/job-status.test.tsx`
- [X] T046 [P] [US2] Add an isolated Playwright queued-job refresh/reopen/cancel flow that preserves the correct token and never starts real GPU work in `apps/web/tests/e2e/job-refresh-cancel.spec.ts`
- [X] T047 [P] [US2] Add Playwright multi-session tests for cross-token status, cancellation, preview, and download denial plus queue isolation in `apps/web/tests/e2e/job-isolation.spec.ts`
- [X] T048 [P] [US2] Add API contract/security coverage for cancel idempotency, wrong/missing tokens, terminal-state cancellation, restart-visible state, and cross-job result denial in `apps/api/tests/contract/test_feature005_job_access.py`

### Implementation for User Story 2

- [X] T049 [US2] Integrate `job-storage.ts` into submission, restoration, terminal-state display, cancellation, and explicit forget behavior while preventing transport errors from deleting a remembered job in `apps/web/app/page.tsx`
- [X] T050 [US2] Run the isolated unit/API/Playwright restoration, cancellation, multi-session, and cross-token suites and record exact counts and retained browser-storage behavior in `evidence/feature-005/us2-local.md`
- [ ] T051 [US2] MANUAL GATE: On the deployed production frontend perform ten refresh/reopen recovery trials across queued/running/terminal states without rerunning expensive GPU work unnecessarily; record accurate outcomes in `evidence/feature-005/us2-refresh-external.md`
- [ ] T052 [US2] MANUAL GATE: On the deployed production route complete five eligible queued-job cancellation trials plus wrong-token denial and verify cancelled state persists after refresh; record sanitized outcomes in `evidence/feature-005/us2-cancel-external.md`

**Checkpoint**: User Story 2 works independently and preserves ownership.

---

## Phase 5: User Story 3 - Receive Safe Capacity and Dependency Failures (Priority: P3)

**Goal**: Users see accurate, understandable, non-sensitive errors for invalid
input, capacity, dependency, timeout, cancellation, missing result, and API
transport failure.

**Independent Test**: Inject each supported failure locally, verify the
frontend maps it to the correct state/message, and prove no response leaks
internal addresses, paths, traces, tokens, or another user's data.

### Tests for User Story 3

- [X] T053 [P] [US3] Add failing frontend tests that distinguish transport/API-unavailable errors from API-confirmed 404/expired jobs and accurately render validation, capacity, dependency, timeout, cancellation, and missing-result states in `apps/web/tests/unit/error-behavior.test.tsx`
- [X] T054 [P] [US3] Extend the CORS matrix to prove an allowed origin without a valid job token remains unauthorized and a denied origin cannot read either success or error bodies in `apps/api/tests/security/test_cors_policy.py`
- [X] T055 [P] [US3] Extend Nginx runtime tests for upstream refusal/timeout/oversized upload/malformed Host and verify generic bounded responses with no upstream/local details in `tests/security/test_nginx_runtime.py`
- [X] T056 [P] [US3] Add a contract test requiring all approved failure-matrix cases, cleanup, state assertions, and secret-safe evidence fields in `tests/security/test_feature005_failure_matrix_contract.py`

### Implementation for User Story 3

- [X] T057 [US3] Add typed network, timeout, malformed-response, and API error handling without mapping network failures to missing jobs in `apps/web/lib/api/jobs.ts`
- [X] T058 [US3] Make polling preserve the last confirmed lifecycle state during transient API/Tunnel failures, stop cleanly on unmount/cancel, and resume safely after recovery in `apps/web/lib/jobs/use-job-status.ts`
- [X] T059 [US3] Render distinct accessible messages and retry guidance for API unavailable, invalid input, capacity, dependency, timeout, cancellation, missing/expired job, and forbidden ownership in `apps/web/components/job-status.tsx`
- [X] T060 [US3] Extend the controlled operations runner with invalid upload, queue full, dependency unavailable, ComfyUI failure, timeout, cancellation race, missing result, Tunnel/API interruption, cleanup, and JSON evidence output in `scripts/windows/run_operations_matrix.ps1`
- [X] T061 [US3] Execute the complete local failure matrix using isolated/mock cases except where the existing approved real adapter is explicitly required, and record commands, expected/actual states, cleanup, and leaks scan in `evidence/feature-005/us3-failure-matrix.md`
- [ ] T062 [US3] MANUAL GATE: With the production frontend deployed, stop only the named Tunnel when no unsafe active work exists, verify frontend availability plus explicit Backend-unavailable behavior, and record restoration at the same API URL in `evidence/feature-005/us3-tunnel-outage.md`

**Checkpoint**: User Story 3 reports failures accurately and safely.

---

## Phase 6: User Story 4 - Preserve the Existing Website (Priority: P4)

**Goal**: Deploying and rolling back Mango74 changes only `/mango74` and leaves
representative unrelated `www.mangosgo.com` paths byte/behavior compatible.

**Independent Test**: Capture authorized pre-deploy response baselines for
representative unrelated paths, compare them after deploy and after rollback,
and verify only `/mango74` behavior changed as approved.

### Tests for User Story 4

- [X] T063 [P] [US4] Add tests for redirect/query preservation, route allowlists, safe external-host restrictions, normalized headers/body hashes, dynamic-field exclusions, and no-write behavior in `tests/security/test_mangosgo_route_baseline_contract.py`

### Implementation for User Story 4

- [X] T064 [P] [US4] Implement a read-only authorized baseline capture tool for `/mango74`, `/mango74/`, release assets, and administrator-supplied representative unrelated routes in `scripts/verify/capture_mangosgo_baseline.py`
- [X] T065 [P] [US4] Implement a comparison tool that flags status, redirect, security-header, content-hash, and unexpected-route changes while excluding only documented dynamic fields in `scripts/verify/compare_mangosgo_baseline.py`
- [ ] T066 [US4] Consolidate the administrator-confirmed NT Server product/version, document root, deployment mechanism, redirect/deep-link mechanism, backup command, rollback command, and authorized route sample from T043 without credentials in `evidence/feature-005/nt-server-inventory.md`
- [ ] T067 [US4] After T066, replace only platform-neutral placeholders with the administrator-confirmed deployment/rollback adapter and preserve the `/mango74`-only boundary in `deploy/nt-server/README.md`
- [ ] T068 [US4] Normalize and validate the timestamped pre-change `/mango74` and unrelated-route baseline captured before T043 into the comparison-tool schema in `evidence/feature-005/routes-before.json`
- [ ] T069 [US4] MANUAL GATE: After deployment compare the production site to T068 and record a PASS only when unrelated routes remain unchanged in `evidence/feature-005/routes-after-deploy.md`
- [ ] T070 [US4] MANUAL GATE: Perform a controlled NT frontend rollback to the T043 backup, compare against T068 to prove the previous `/mango74` state and unrelated routes are restored, then restore the approved release and record both checks in `evidence/feature-005/routes-after-rollback.md`

**Checkpoint**: User Story 4 proves path isolation before declaring production
success.

---

## Phase 7: User Story 5 - Deploy, Monitor, Restart, and Roll Back (Priority: P5)

**Goal**: The operator can install, validate, monitor, restart, recover, and
independently roll back the static frontend and single-Notebook AI Backend.

**Independent Test**: From a staged baseline, validate/install services,
observe health, run three controlled restart trials, interrupt/recover the
Tunnel at the same hostname, and rehearse frontend and Backend rollbacks
independently without false job completion or lost durable metadata.

### Tests for User Story 5

- [X] T071 [P] [US5] Extend service-contract tests for explicit Caddy-to-Nginx cutover order, reversible disabled Caddy definition, Nginx validation-before-start, no dual bind on 8080, and least-privilege service accounts in `tests/security/test_feature005_services_contract.py`
- [X] T072 [P] [US5] Add recovery-runner tests for preflight refusal with active unsafe work, ComfyUI/API/Nginx/cloudflared restart order, three trials, durable state snapshots, readiness timeout, rollback trigger, and evidence redaction in `tests/security/test_feature005_recovery_contract.py`

### Implementation for User Story 5

- [X] T073 [US5] Update the WinSW installer to validate Nginx binary hash/config, install `Local3D-Nginx`, stop/disable but preserve `Local3D-Caddy` for rollback, avoid dual port ownership, and support non-starting dry-run validation in `scripts/windows/install_winsw_services.ps1`
- [X] T074 [P] [US5] Implement an idempotent Nginx start script that validates configuration, verifies port 8080 ownership, refuses public binding, starts only `Local3D-Nginx`, and confirms Host/path health in `scripts/windows/start_nginx_service.ps1`
- [X] T075 [P] [US5] Implement an idempotent Nginx stop script that preserves config/log evidence, waits boundedly, confirms port release, and never stops unrelated processes in `scripts/windows/stop_nginx_service.ps1`
- [X] T076 [US5] Extend service verification for ComfyUI, API, Nginx, named cloudflared, disabled Caddy rollback state, executable hashes, listener ownership, readiness, and non-secret JSON output in `scripts/windows/verify_services.ps1`
- [X] T077 [US5] Implement a resumable three-trial recovery runner with active-job safety gate, pre/post durable-state snapshots, controlled service restarts, readiness waits, no-false-terminal assertions, and explicit reboot exclusion unless separately authorized in `scripts/windows/run_feature005_recovery_matrix.ps1`
- [X] T078 [P] [US5] Implement a sanitized deployment evidence recorder that accepts hashes, change/rollback IDs, service/route outcomes, and timings but rejects credentials, tokens, private config, user files, and model bytes in `scripts/verify/record_feature005_deployment.py`
- [X] T079 [P] [US5] Write the exact operator sequence for preflight, static package handoff, Nginx cutover, named-Tunnel activation, health diagnosis, service restart, safe active-job handling, and escalation in `docs/runbooks/mango74-production.md`
- [X] T080 [P] [US5] Write independent NT frontend, Nginx/Caddy, named-Tunnel, API, workflow, and configuration rollback procedures with stop criteria and post-rollback verification in `docs/runbooks/mango74-rollback.md`
- [X] T081 [US5] MANUAL GATE: In an elevated shell verify the approved Nginx binary hash, install/start `Local3D-Nginx`, disable but retain `Local3D-Caddy`, and record config validation, service state, loopback listener, and Host/path health in `evidence/feature-005/nginx-service-install.md`
- [X] T082 [US5] MANUAL GATE: Through the authorized secure process install/start the named cloudflared Windows service without recording its token, then record service state, connector health, hostname, and redacted configuration result in `evidence/feature-005/cloudflared-service-install.md`
- [ ] T083 [US5] Run the complete local health chain after T081-T082 and record ComfyUI/API/Nginx/GPU/storage/workflow/Tunnel/CORS/listener/process results without converting unavailable dependencies into PASS in `evidence/feature-005/health-chain.md`
- [ ] T084 [US5] With explicit operator control and no unsafe active job, stop/restart only cloudflared, verify fixed-hostname loss/recovery and accurate durable job state, and record timings in `evidence/feature-005/tunnel-recovery.md`
- [ ] T085 [US5] Execute controlled service restart trial 1 across ComfyUI, API, Nginx, and cloudflared and record pre/post job-state counts plus readiness recovery in `evidence/feature-005/restart-trial-1.md`
- [ ] T086 [US5] Execute controlled service restart trial 2 across ComfyUI, API, Nginx, and cloudflared and record pre/post job-state counts plus readiness recovery in `evidence/feature-005/restart-trial-2.md`
- [ ] T087 [US5] Execute controlled service restart trial 3 across ComfyUI, API, Nginx, and cloudflared and record pre/post job-state counts plus readiness recovery in `evidence/feature-005/restart-trial-3.md`
- [ ] T088 [US5] MANUAL GATE: Rehearse the NT Server frontend rollback using the recorded backup identifier without changing the AI Backend, verify elapsed time and routes, then restore the approved release in `evidence/feature-005/frontend-rollback.md`
- [ ] T089 [US5] Rehearse the Notebook Backend/Nginx/Tunnel rollback without redeploying static frontend files, preserve durable job metadata, and record accurate frontend-unavailable behavior plus recovery in `evidence/feature-005/backend-rollback.md`
- [ ] T090 [US5] Consolidate service hashes/states, listener boundaries, three restart trials, Tunnel recovery, independent rollback results, elapsed times, and remaining manual blockers in `evidence/feature-005/us5-operations.md`

**Checkpoint**: User Story 5 is operationally reproducible and rollback-safe.

---

## Phase 8: User Story 6 - Use a Firebase Frontend Preview Safely (Priority: P6)

**Goal**: Firebase remains an optional static-frontend preview; without API
permission it reports Backend unavailability accurately, and with its exact
temporary origin allowlisted it can run a controlled flow until permission is
removed independently.

**Independent Test**: Deploy the validated preview build, verify accurate
unavailable behavior with preview CORS disabled, enable only the exact Firebase
origin for a controlled flow, remove it, and prove production origin behavior
is unchanged.

### Tests for User Story 6

- [X] T091 [P] [US6] Add frontend configuration tests for preview labeling, exact stable API selection, missing/unavailable API behavior, and refusal to represent Firebase as the official production URL in `apps/web/tests/unit/firebase-preview.test.tsx`
- [X] T092 [P] [US6] Add an isolated Playwright preview test proving API network/CORS failure displays Backend unavailable rather than “This job is no longer available” in `apps/web/tests/e2e/firebase-preview-unavailable.spec.ts`
- [X] T093 [P] [US6] Add an isolated Playwright/API test proving only the exact Firebase origin works when enabled, production remains allowed, and Firebase access stops after independent removal in `apps/web/tests/e2e/firebase-preview-cors.spec.ts`

### Implementation for User Story 6

- [X] T094 [US6] Add explicit frontend preview-mode configuration and validation without weakening production hostname/base-path/API rules in `apps/web/lib/config/public-runtime.ts`
- [X] T095 [US6] Render a clear Firebase preview label and accurate API-unavailable state while retaining the official Mango74 link and normal production presentation in `apps/web/app/page.tsx`
- [X] T096 [US6] Build and validate a Firebase static preview using the same stable API base and static-content security scan, then record the release/channel, hash, and preview-mode result in `evidence/feature-005/firebase-package.md`
- [X] T097 [US6] MANUAL GATE: Deploy only the validated preview artifact to Firebase and verify the no-API-permission path reports Backend unavailable without touching production configuration in `evidence/feature-005/firebase-preview-disabled.md`
- [ ] T098 [US6] MANUAL GATE: Temporarily enable only `https://inw3d-ai-local.web.app`, run one controlled preview flow, remove the permission, prove access stops while `https://www.mangosgo.com` remains allowed, and record no credential values in `evidence/feature-005/firebase-preview-enabled-then-removed.md`

**Checkpoint**: User Story 6 is an independently removable preview and not a
Backend or production replacement.

---

## Phase 9: Polish & Cross-Cutting Validation

**Purpose**: Close traceability, regression, security, documentation, external
boundary, and release-readiness gates across all stories.

- [X] T099 [P] Update the repository architecture guide with the final NT static frontend, separate stable API, named Tunnel, Nginx loopback, single-Notebook runtime, trust boundaries, and rollback topology in `docs/architecture/feature-005-production.md`
- [X] T100 Run the complete API/security/contract suites, Ruff, mypy, frontend unit tests, typecheck, lint, all isolated Playwright tests, Nginx validation, PowerShell parsing, package validation, and targeted integration tests; record exact commands/counts/skips/failures in `evidence/feature-005/regression.md`
- [X] T101 Run tracked-file, built-archive, generated-manifest, Nginx/cloudflared config, and public-response scans for secrets, internal addresses, raw tokens, Quick Tunnel URLs, private paths, uploads/models/GLBs, and sensitive logs; record only sanitized findings in `evidence/feature-005/security-scan.md`
- [X] T102 Execute every currently available repository/local step in `specs/005-nginx-mango74-deployment/quickstart.md`, record deviations and environment-dependent gates, and correct the guide only when observed behavior proves it inaccurate in `evidence/feature-005/quickstart-validation.md`
- [ ] T103 MANUAL GATE: From an authorized independent network verify the stable frontend/API are reachable only through approved hostnames and ports 3000/8000/8080/8188 plus any raw Notebook address provide no usable application route; do not probe `161.200.90.4` without explicit network-administrator authorization, and record scope/results in `evidence/feature-005/external-boundary.md`
- [X] T104 Map every Feature 005 user story, FR/SR/FB/SC requirement, contract, implementation file, test, and evidence gate; identify any uncovered requirement without inventing completion in `evidence/feature-005/requirements-traceability.md`
- [X] T105 Re-run the Constitution 5.0.0 compliance review after implementation and record single-Notebook, split-origin, exact CORS, named-Tunnel, Nginx-only origin, secret, test, architecture-approval, and external-evidence outcomes in `evidence/feature-005/constitution-compliance.md`
- [X] T106 Record the final task totals, commands actually run, deployed release hashes, service/route states, real-GPU result, external acceptance, restart/rollback outcomes, blockers, and exact operator follow-ups without assumptions in `evidence/feature-005/final-validation.md`
- [X] T107 Declare production ready only when T044, T051-T052, T062, T068-T070, T081-T090, T097-T098, and T103 have real evidence and every mandatory test passes; otherwise record an explicit NO-GO with owners and next actions in `evidence/feature-005/release-decision.md`

---

## Dependencies & Execution Order

### Phase dependencies

- **Phase 1 (Setup)**: Starts immediately.
- **Phase 2 (Foundational)**: Depends on Phase 1 and blocks all user stories.
- **US1 (P1)**: Depends on Phase 2. T042 depends on T041; T043 depends on
  T039 and includes the NT inventory, route baseline, and backup gate before
  deployment; T044 depends on T042-T043.
- **US2 (P2)**: Depends on T018-T019 and T034. Local tests do not require
  production deployment; T051-T052 depend on T042-T044.
- **US3 (P3)**: Depends on T016-T018, T021, and T034. T062 depends on the
  production frontend and named Tunnel.
- **US4 (P4)**: Tooling begins after Phase 2 and T043. T063-T065 create the
  reusable validators, T066-T068 normalize the inventory and true pre-change
  baseline captured by T043, T069 checks the deployed state, and T070 performs
  the story-specific rollback/restore comparison.
- **US5 (P5)**: Service code can begin after Phase 2. T081 depends on Nginx
  validation and administrator elevation; T082 depends on T042; T083-T087
  depend on T081-T082; T088 depends on T043/T068; T089 depends on an approved
  local rollback baseline.
- **US6 (P6)**: Local tests/build can begin after Phase 2. T097 depends on an
  authorized Firebase deployment; T098 additionally depends on T042 and the
  authorized temporary CORS change.
- **Phase 9 (Polish)**: T099/T104 can start after repository implementation;
  final GO/NO-GO requires all mandatory story and manual gates.

### User-story dependency graph

```text
Setup → Foundational → US1 ───────→ Production external acceptance
                       ├─→ US2 ───→ Refresh/cancel external trials
                       ├─→ US3 ───→ Tunnel outage/recovery
                       ├─→ US4 ───→ Route isolation/rollback proof
                       ├─→ US5 ───→ Service/restart/rollback proof
                       └─→ US6 ───→ Optional Firebase permission cycle
All completed mandatory stories → Polish → GO/NO-GO
```

### Within each user story

1. Add the story's failing tests/contracts first and confirm they exercise the
   intended gap.
2. Implement only the behavior required by those tests and the approved plan.
3. Run story-local validation and record sanitized evidence.
4. Execute administrator/external/manual gates only after local prerequisites
   pass.
5. Mark a task `[X]` only after its exact acceptance and evidence target pass.

### Parallel opportunities

- T003-T006 can run in parallel after T001 establishes the baseline.
- T007-T015 are independent test files and can run in parallel.
- T018-T019, T022-T023, and T026-T027 can run in parallel after their tests
  exist.
- US1 test tasks T030-T033 can run in parallel; T038 can run alongside frontend
  implementation.
- US2 test tasks T045-T048 can run in parallel.
- US3 test tasks T053-T056 can run in parallel.
- US4 tooling tasks T063-T065 can run in parallel before production capture.
- US5 test/document tasks T071-T072 and T078-T080 can run in parallel.
- US6 test tasks T091-T093 can run in parallel.
- Manual Cloudflare, NT Server, and Firebase administrator actions must not run
  in parallel when either action would obscure the deployment baseline or
  rollback evidence.

---

## Parallel Example: User Story 1

```text
Agent A: T030 in apps/web/tests/unit/generation-flow.test.tsx
Agent B: T031 in apps/web/tests/e2e/production-cross-origin.spec.ts
Agent C: T032 in tests/security/test_nginx_runtime.py
Agent D: T033 in tests/security/test_feature005_external_acceptance_contract.py
```

## Parallel Example: User Story 5

```text
Agent A: T071 in tests/security/test_feature005_services_contract.py
Agent B: T072 in tests/security/test_feature005_recovery_contract.py
Agent C: T079 in docs/runbooks/mango74-production.md
Agent D: T080 in docs/runbooks/mango74-rollback.md
```

---

## Implementation Strategy

### MVP first

1. Complete Setup and Foundational phases.
2. Complete US1 through T041 for a validated local Nginx→FastAPI→ComfyUI→RTX
   flow and a deployable `front-end.zip`.
3. Obtain the authorized named-Tunnel and NT Server gates (T042-T043).
4. Complete T044 from a genuinely independent network.
5. Stop and validate before expanding to P2-P6 stories.

### Incremental delivery

1. **Local deployable baseline**: T001-T041.
2. **Production happy path**: T042-T044.
3. **Durable ownership/cancellation**: T045-T052.
4. **Safe failure behavior**: T053-T062.
5. **Unrelated-route preservation**: T063-T070.
6. **Operations and independent rollback**: T071-T090.
7. **Optional Firebase preview**: T091-T098.
8. **Cross-cutting validation and release decision**: T099-T107.

### Completion rules

- Repository tests passing does not complete an administrator or external task.
- Existing Feature 004 evidence may be referenced only when it proves the exact
  current Feature 005 route, proxy, workflow revision, and acceptance condition.
- A generated script/config is not runtime evidence.
- A random `trycloudflare.com` URL is never production evidence.
- CORS approval never replaces job-token ownership or abuse controls.
- Do not record Tunnel tokens, Cloudflare credentials, job tokens, user inputs,
  model files, generated GLBs, private environment configuration, or sensitive
  logs in `evidence/feature-005/`.

---

## Task Summary

- **Total tasks**: 107
- **Setup**: 6 tasks
- **Foundational**: 23 tasks
- **US1 (P1)**: 15 tasks
- **US2 (P2)**: 8 tasks
- **US3 (P3)**: 10 tasks
- **US4 (P4)**: 8 tasks
- **US5 (P5)**: 20 tasks
- **US6 (P6)**: 8 tasks
- **Polish/cross-cutting**: 9 tasks
- **Suggested MVP**: T001-T044 (local MVP at T041; production MVP after
  authorized T042-T044)
