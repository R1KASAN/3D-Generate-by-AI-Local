# Feature Specification: Mango74 Production Path Deployment

**Feature Branch**: `main` (no feature branch was created)

**Feature Directory**: `005-nginx-mango74-deployment`

**Created**: 2026-09-08

**Status**: Clarified — constitution alignment required before planning

**Input**: User description: "Serve the compiled Mango74 frontend from the
existing NT Server at exactly https://www.mangosgo.com/mango74/. The browser
calls a separate authorized stable HTTPS AI API origin using an exact CORS
allowlist. That API reaches the current RTX 5070 Notebook through a named
Cloudflare Tunnel, cloudflared, loopback Nginx, FastAPI, and ComfyUI. Preserve
all unrelated www.mangosgo.com paths and do not assume that 161.200.90.4
belongs to the current Notebook."

**Supersedes**: The production-access assumptions of feature
`004-secure-ai-test-access`. Feature 004 remains unchanged as the historical
record for temporary Quick Tunnel and Caddy validation. Its validated job,
authorization, generation, cancellation, recovery, and result behavior remains
the functional baseline unless this specification strengthens it.

## Clarifications

### Session 2026-09-08

- Q: Should only the `/mango74` path be routed to this AI service? → A: Yes;
  only `/mango74` and its explicitly defined child paths may route to the AI
  service.
- Q: Should all other paths of `www.mangosgo.com` remain unchanged? → A: Yes;
  unrelated paths must preserve their existing behavior before, during, and
  after deployment or rollback.
- Q: Should Cloudflare route `/mango74` through a Cloudflare Tunnel to
  `cloudflared` running on the Notebook, with the Tunnel origin pointing to
  Nginx at `127.0.0.1:8080`, instead of connecting directly to
  `161.200.90.4:443`? → A: Yes; use the outbound Tunnel path and do not expose
  direct inbound HTTPS to the Notebook origin.
- Q: Should `/mango74` be public to anyone with the URL or require Cloudflare
  Access sign-in? → A: Public; no site-wide or Cloudflare Access sign-in is
  required, while per-job access controls and resource limits remain mandatory.
- Q: What currently serves `www.mangosgo.com`? → A: Unknown; the authorized
  administrator must identify and record the current production origin before
  any routing change or rollback plan is approved.

### Session 2026-09-09

- Q: What exact stable production API boundary will the Mango74 frontend use?
  → A: The earlier same-origin `/mango74/api/*` decision is superseded by the
  revised cross-origin model. The API will use a separate authorized stable
  HTTPS origin; its exact value is resolved by the subsequent clarification.
- Q: Who is responsible for the Cloudflare route and NT Server deployment?
  → A: An authorized Cloudflare Zone administrator configures and approves the
  stable API hostname and named Tunnel route, while an authorized NT Server
  administrator deploys and rolls back only the compiled `/mango74/` frontend;
  the named operators must be recorded before either production action.
- Q: Which physical machine will operate the production AI backend? → A: The
  current Notebook with the RTX 5070 is the Production AI Server; its machine
  identity must be validated independently of any assumed public IP address.
- Q: What exact stable production API origin and public API base path will the
  Mango74 frontend call? → A:
  `https://mango74-api.mangosgo.com/api/*`; the authorized Cloudflare
  administrator must provision this hostname to the named Tunnel before
  production acceptance.

### Governance Alignment

Constitution 4.0.0 still defines the Notebook as the sole application server,
places the frontend behind Nginx on that Notebook, and binds the approved
production Tunnel boundary to the Mango74 path. The revised requirement places
compiled frontend files on the existing NT Server and gives the AI API a
separate stable public origin. Planning and implementation MUST remain blocked
until an approved constitution amendment or governance exception explicitly
permits this split frontend/backend and cross-origin API deployment while
preserving one Notebook as the sole AI backend and compute server.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Generate a 3D Asset at Mango74 (Priority: P1)

A public user opens the static frontend at the exact Mango74 HTTPS path,
submits a supported reference image through the authorized stable API route,
follows the accepted job, and receives a previewable and downloadable 3D
result without needing to know the Notebook address or internal services.

**Why this priority**: This is the complete user outcome and proves that the
existing generation service works from its authorized production location.

**Independent Test**: From a network outside the Notebook's local network, an
evaluator can open the Mango74 path, submit one valid image through the stable
API route, observe the job reach a terminal state, and preview and download the
completed GLB using only approved public URLs.

**Acceptance Scenarios**:

1. **Given** the production route is healthy, **When** a user opens
   `https://www.mangosgo.com/mango74`, **Then** the browser reaches
   `/mango74/` through one safe redirect and the generation interface loads.
2. **Given** the interface has loaded, **When** its styles, scripts, images,
   and other application assets are requested, **Then** they load successfully
   from the NT Server without escaping the `/mango74` path boundary.
3. **Given** a valid supported image, **When** the user submits a request,
   **Then** the browser uses only the separate authorized stable API origin,
   the exact production frontend origin is accepted, and the service returns
   the reference and access information needed to follow the job.
4. **Given** a successfully completed job, **When** its authorized user opens
   the result, **Then** the user can preview and download the same finalized
   textured GLB.

---

### User Story 2 - Resume and Cancel Work After Refresh (Priority: P2)

A user can refresh or reopen an authorized job view, recover its current
durable state, and cancel their own queued job without operator assistance.

**Why this priority**: Generation can take long enough that browser refreshes
and changes of mind are normal; users must not lose control of their accepted
work.

**Independent Test**: An evaluator submits a job while processing capacity is
occupied, refreshes or reopens the page, recovers the same queued job, cancels
it, and verifies that it remains cancelled and never receives a result.

**Acceptance Scenarios**:

1. **Given** an authorized non-terminal job, **When** the user refreshes or
   reopens its deep link, **Then** the same job and its current durable state
   are displayed without an incorrect not-found response.
2. **Given** an authorized queued job, **When** the user cancels it after a
   refresh, **Then** the job reaches and remains in the cancelled state.
3. **Given** a completed job, **When** its authorized user refreshes the result
   view, **Then** preview and download access remain available for the approved
   retention period.
4. **Given** missing, invalid, expired, or cross-job access information,
   **When** a visitor opens a job deep link, **Then** no job existence,
   metadata, state, preview, or result is disclosed.

---

### User Story 3 - Receive Safe Capacity and Dependency Failures (Priority: P3)

A user receives understandable, non-sensitive guidance when input is invalid,
capacity is exhausted, generation fails, an internal dependency is unavailable,
or the public route cannot complete the request.

**Why this priority**: Production exposure must fail predictably without
leaking the Notebook address, internal ports, implementation details, or other
users' data.

**Independent Test**: An evaluator induces each documented input, capacity,
dependency, timeout, cancellation, and missing-result condition and verifies
that each response is safe, accurate, and confined to the Mango74 boundary.

**Acceptance Scenarios**:

1. **Given** invalid or unsupported input, **When** a user submits it,
   **Then** the request is rejected before generation with correction guidance.
2. **Given** no available admission capacity, **When** a user submits new
   work, **Then** the service refuses it safely without disturbing accepted
   jobs.
3. **Given** a required dependency is unavailable, **When** a public request
   depends on it, **Then** the user receives a generic service-unavailable
   outcome and no internal address, path, stack trace, or secret is disclosed.
4. **Given** a job fails, times out, is cancelled, or lacks a valid finalized
   output, **When** the user checks it, **Then** its accurate terminal outcome
   is shown and no incomplete download is offered.
5. **Given** the frontend loads but the stable API cannot be reached, **When**
   the user attempts to submit or restore a job, **Then** the interface reports
   AI service unavailability rather than incorrectly declaring the job absent.

---

### User Story 4 - Preserve the Existing Website (Priority: P4)

Visitors using other `www.mangosgo.com` paths continue to receive their
existing content and behavior while the Mango74 application is deployed,
operated, or rolled back.

**Why this priority**: The new application shares a hostname with an existing
site and must not take control of unrelated routes.

**Independent Test**: Before deployment, an authorized evaluator records a
representative baseline of non-Mango74 routes; after deployment and after
rollback, every baseline route retains its expected status, destination, and
content identity.

**Acceptance Scenarios**:

1. **Given** a request whose path is outside `/mango74`, **When** it reaches
   `www.mangosgo.com`, **Then** it is not captured, rewritten, redirected, or
   served by the Mango74 application.
2. **Given** an ambiguous look-alike path such as `/mango740` or a differently
   cased path, **When** it is requested, **Then** it is not treated as part of
   the Mango74 application.
3. **Given** the Mango74 application is unavailable, **When** a visitor uses an
   unrelated site path, **Then** that path remains unaffected.

---

### User Story 5 - Deploy, Monitor, Restart, and Roll Back (Priority: P5)

The project operators can validate the complete path, deploy the compiled
frontend to the NT Server, operate the AI backend on the approved Notebook,
identify a failing layer, restart backend services, and roll back either side
without losing or falsely completing jobs.

**Why this priority**: A production route is acceptable only when its effects
are observable and its change can be reversed safely.

**Independent Test**: The authorized operators perform a staged frontend and
backend deployment, verify each health layer and the external route, restart
backend services, execute both rollback procedures, and confirm job accuracy
plus preservation of unrelated site paths throughout the exercise.

**Acceptance Scenarios**:

1. **Given** all local services are ready, **When** the operator checks health,
   **Then** the public route, web experience, job service, AI workflow,
   processing device, storage, and Tunnel boundary are distinguishable.
2. **Given** one component has restarted, **When** the service recovers,
   **Then** accepted jobs are not lost, duplicated, or falsely completed.
3. **Given** a production acceptance check fails, **When** rollback is invoked,
   **Then** the previous public behavior is restored without application data
   migration or corruption of accepted job records.
4. **Given** rollback has completed, **When** Mango74 and unrelated baseline
   paths are retested, **Then** their documented rollback outcomes are met.
5. **Given** the named Tunnel or backend services restart, **When** readiness
   returns, **Then** the same stable API URL works without rebuilding or
   redeploying the NT-hosted frontend.

---

### User Story 6 - Use a Firebase Frontend Preview Safely (Priority: P6)

A reviewer can open the optional Firebase-hosted frontend preview and receive
an accurate outcome whether or not an authorized stable AI API is available.

**Why this priority**: Firebase is useful for reviewing compiled frontend
behavior, but it must not be mistaken for the production location or appear to
offer working generation when no backend route exists.

**Independent Test**: A reviewer opens the Firebase preview first without an
available API and then with an explicitly enabled test API, confirming that
the interface reports the correct state in both cases and never silently uses
a temporary or unauthorized backend.

**Acceptance Scenarios**:

1. **Given** no approved API is configured, **When** a reviewer opens the
   Firebase preview or attempts generation, **Then** the interface clearly
   reports that AI processing is unavailable and does not restore a stale job
   as if it were reachable.
2. **Given** an approved test API and exact preview-origin permission are
   enabled, **When** a reviewer submits a valid request, **Then** the preview
   can complete the documented job flow without accepting another origin.
3. **Given** the Firebase preview is available, **When** a visitor compares its
   address with the production address, **Then** it is clearly represented as
   a non-production frontend preview.

### Edge Cases

- `/mango74` is requested with a query string or fragment before redirection.
- `/mango74/` is requested with repeated slashes, dot segments, percent-encoded
  separators, mixed case, or path traversal sequences.
- A look-alike path such as `/mango740`, `/Mango74`, or `/mango74-example` is
  requested.
- A user refreshes a nested job, preview, or result view directly.
- An application asset, API request, redirect, preview, or download is built
  with an incorrect frontend base path or stable API base URL.
- The static frontend loads correctly but its configured stable API origin is
  missing, unavailable, expired, unauthorized, or replaced by a temporary URL.
- A browser retains a job reference created through a different deployment or
  API route and then opens the NT Server or Firebase frontend.
- A cross-origin preflight comes from the production frontend, the Firebase
  preview, an HTTP downgrade, a look-alike origin, an unexpected port, `null`,
  or an unapproved website.
- Cached pre-deployment content conflicts with the new route or a deployment
  change has not propagated consistently.
- The public route is healthy while the web application, job service, AI
  workflow, processing device, or storage is unavailable.
- The Notebook backend is reachable directly without passing through the
  approved Tunnel boundary.
- Plain HTTP, an invalid certificate, an expired certificate, or an
  unauthenticated origin connection is attempted.
- A browser disconnects during upload, queueing, processing, cancellation,
  preview, or download.
- A queued job is cancelled at nearly the same time that processing begins.
- The result reports completion but the GLB is partial, corrupt, missing, or
  associated with another job.
- A deployment or rollback occurs while jobs are queued or running.
- The stable API or Mango74 frontend fails while unrelated
  `www.mangosgo.com` paths remain in use.
- A configuration intended for development is accidentally selected for the
  production endpoint.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The service MUST be available to public users at exactly
  `https://www.mangosgo.com/mango74/` after production acceptance succeeds.
- **FR-002**: A request to `/mango74` MUST reach `/mango74/` through one
  permanent, HTTPS-preserving redirect without losing its query string.
- **FR-003**: The service MUST treat `/mango74` and its explicitly defined
  child paths as the complete public frontend boundary; API operations MUST use
  the separately authorized stable API origin.
- **FR-004**: Every first-party page, navigation target, script, stylesheet,
  image, and other frontend asset MUST work within the approved `/mango74/`
  boundary, while every API operation, status lookup, cancellation, preview,
  and download MUST use the approved stable API boundary.
- **FR-005**: Refreshing or directly opening a valid nested application URL
  MUST return the intended application view rather than an incorrect not-found
  response.
- **FR-006**: Paths outside the exact Mango74 boundary MUST NOT be captured,
  rewritten, redirected, cached, or served by the Mango74 application.
- **FR-007**: The public interface MUST allow a user to submit one supported
  reference image for an AI/3D generation job using the existing validated
  input rules.
- **FR-008**: Every accepted job MUST receive an opaque job reference and the
  unguessable access information required to revisit that job.
- **FR-009**: The service MUST report each job as queued, running, completed,
  failed, or cancelled and MUST permit only documented valid transitions.
- **FR-010**: The latest durable job state and authorized access MUST survive
  browser refresh, reconnection, supported component restart, and Notebook
  restart according to the existing recovery contract.
- **FR-011**: An authorized user MUST be able to cancel their own queued job,
  including after refreshing or reopening its job view.
- **FR-012**: A cancelled queued job MUST not start processing, consume a new
  generation slot, or expose a generated result.
- **FR-013**: A completed job MUST provide one finalized textured GLB that its
  authorized user can preview and download.
- **FR-014**: Preview and download MUST refer to the same finalized bytes and
  MUST remain protected by the job's access boundary.
- **FR-015**: Missing, invalid, expired, or cross-job access information MUST
  reveal neither job existence nor job state, metadata, preview, or output.
- **FR-016**: The service MUST provide safe user-facing outcomes for invalid
  input, capacity exhaustion, unavailable dependencies, failed generation,
  timeout, cancellation, missing output, restart recovery, and public-route
  failure.
- **FR-017**: Public errors MUST NOT disclose the origin IP, internal ports,
  local filesystem paths, upstream identities, stack traces, credentials, or
  another user's information.
- **FR-018**: A job MUST NOT be reported as completed until its output is
  finalized, readable, valid for its declared type, and associated with the
  correct authorized job.
- **FR-019**: The application MUST preserve the existing single-Notebook GPU
  admission, queueing, storage, timeout, retention, and cleanup limits unless a
  separately approved requirement changes them.
- **FR-020**: The current Notebook with the RTX 5070 MUST be the single
  Production AI Server operating FastAPI, durable job storage, workflow files,
  models, ComfyUI, and GPU execution. Its production identity MUST be recorded
  using validated machine evidence and MUST NOT depend on an assumed public IP
  address.
- **FR-021**: Public production API traffic MUST pass through Cloudflare and an
  authorized named Cloudflare Tunnel to `cloudflared` on the Notebook before
  it reaches Nginx at `127.0.0.1:8080`; direct inbound application access
  through any public IP MUST NOT be required. Restarting the Tunnel or Notebook
  MUST restore the same stable public API URL.
- **FR-022**: The NT Server MUST serve only the compiled Mango74 frontend files
  and static assets under `/mango74/`; it MUST NOT run the job service, durable
  job storage, AI workflow, model files, ComfyUI, or GPU workloads.
- **FR-023**: The AI Notebook's reverse proxy, API, AI workflow, and
  GPU-management services MUST remain loopback-only and inaccessible directly
  from the Internet. The Tunnel MUST reach only the approved reverse-proxy
  origin at `127.0.0.1:8080`.
- **FR-024**: The authorized stable production API boundary MUST be exactly
  `https://mango74-api.mangosgo.com/api/*`. It MUST remain stable across normal
  frontend, backend, Nginx, Notebook, and Tunnel restarts and MUST route
  through the protected named Tunnel to the AI Notebook.
- **FR-025**: An authorized Cloudflare Zone administrator MUST configure and
  approve the separate stable API hostname and named Tunnel route. An
  authorized NT Server administrator MUST deploy and roll back only the
  compiled `/mango74/` frontend. The deployment record MUST identify the named
  operators before either production action is performed.
- **FR-026**: Production release MUST be blocked until a baseline proves which
  unrelated `www.mangosgo.com` paths must be preserved and post-change checks
  confirm those paths remain unaffected.
- **FR-027**: The operator MUST be able to determine independently whether the
  NT-hosted frontend, stable API route, Tunnel, job service, storage, AI
  workflow, and processing device are ready.
- **FR-028**: The operator MUST have reproducible procedures for staged
  validation, deployment, startup, shutdown, restart, diagnosis, and rollback.
- **FR-029**: A failed deployment or acceptance gate MUST be recoverable to the
  recorded pre-deployment state without migrating application data or
  misreporting accepted jobs.
- **FR-030**: Deployment and rollback records MUST state the actual commands or
  authorized actions performed, outcomes, timestamps, affected boundaries, and
  unresolved blockers without recording secrets or private user content.
- **FR-031**: The feature MUST NOT purchase another domain, create another
  unauthorized public hostname, add WireGuard, use cloud GPU compute, or expose
  an internal Notebook service directly.
- **FR-032**: Anyone with the public Mango74 URL MUST be able to load and use
  the generation interface without site-wide sign-in or Cloudflare Access.
  Public availability MUST NOT weaken per-job access credentials, input
  validation, admission controls, queue bounds, or resource limits.
- **FR-033**: The API MUST permit cross-origin browser access from exactly
  `https://www.mangosgo.com` in production. If the Firebase preview is
  explicitly connected for testing, the API MAY additionally permit exactly
  `https://inw3d-ai-local.web.app`. Wildcard, look-alike, HTTP-downgraded,
  unexpected-port, `null`, and all other origins MUST receive no usable
  cross-origin response, and the preview permission MUST be removable without
  changing the production allowlist.
- **FR-034**: Cross-origin permission MUST NOT be represented as authentication
  or protection against direct API abuse; existing job credentials, input
  validation, admission limits, and safe error behavior MUST remain enforced.
- **FR-035**: Firebase Hosting MAY provide a non-production compiled-frontend
  preview, but it MUST NOT host the AI backend or replace the production
  Mango74 URL.
- **FR-036**: When a frontend deployment has no authorized reachable API, it
  MUST clearly report AI processing as unavailable and MUST NOT display a stale
  stored job as though that job were available from the current API boundary.
- **FR-037**: A Firebase preview origin MAY reach the backend only while its
  exact origin is explicitly enabled for testing and MUST be removable without
  changing the production allowlist.
- **FR-038**: A temporary `trycloudflare.com` URL MUST NOT be stored, embedded,
  or represented as the stable production API endpoint.
- **FR-039**: The addresses observed on the current development Notebook—local
  IPv4 `10.203.152.255` and outbound IPv4 `161.200.189.16`—MUST be treated only
  as dated observations, not proof of production identity or inbound
  reachability. `161.200.90.4` MUST NOT be claimed as bound to this machine
  without administrator evidence.
- **FR-040**: No direct public-IP backend route may be selected or tested until
  a network administrator confirms address ownership, reachability, firewall
  authority, and the resulting architecture is approved. The approved Tunnel
  design MUST NOT depend on that confirmation.
- **FR-041**: The compiled production frontend MUST be configured with only the
  approved stable API base URL and MUST NOT call localhost, loopback, a private
  or public Notebook address, ComfyUI, or a temporary Tunnel URL.
- **FR-042**: Job creation, status, cancellation, preview, and download MUST
  remain compatible with the existing `/api/*` contract through the stable API
  boundary. Any public-to-internal prefix transformation MUST be explicit and
  MUST NOT change operation semantics or job authorization.
- **FR-043**: Public API responses and generated operation locations MUST use
  the stable API boundary or safe relative references and MUST NOT expose
  localhost, loopback, Notebook addresses, ComfyUI addresses, temporary Tunnel
  URLs, or local filesystem paths.
- **FR-044**: Cross-origin preflight handling MUST allow only the methods and
  headers required by the existing API contract, including the job-token
  header. Browser credential sharing MUST remain disabled unless a separately
  approved cookie-based requirement makes it necessary.
- **FR-045**: An unreachable or interrupted API MUST be distinguished from an
  API-confirmed missing or expired job so that a network failure cannot be
  presented as "This job is no longer available."

### Security Requirements

- **SR-001**: All production browser traffic MUST use HTTPS. The public
  frontend MUST fail closed when its approved certificate is unavailable, and
  the public API MUST fail closed when Cloudflare cannot provide its approved
  certificate or protected Tunnel route. Loopback HTTP between `cloudflared`
  and the reverse proxy is permitted because it never leaves the Notebook.
- **SR-002**: A direct-to-origin probe MUST not provide usable application
  access outside the approved Cloudflare-fronted request path, unless an
  explicitly approved exception documents compensating controls and expiry.
- **SR-003**: External input MUST be checked for supported content, integrity,
  size, filename, and path safety before admission to the AI workflow.
- **SR-004**: Job credentials, Cloudflare credentials, certificate private
  keys, tokens, passwords, user inputs, generated assets, and private local
  configuration MUST NOT enter version control or unsafe diagnostic output.
- **SR-005**: Public responses and logs MUST preserve useful request and job
  correlation while redacting credentials and sensitive user content.
- **SR-006**: Ambiguous, malformed, or encoded requests MUST NOT bypass the
  exact `/mango74` boundary or reach unintended upstream behavior.
- **SR-007**: Cross-origin responses MUST be denied unless the request origin
  exactly matches an approved environment-specific allowlist entry; wildcard
  origins, look-alike origins, HTTP downgrades, unexpected ports, and the
  `null` origin MUST NOT be accepted.
- **SR-008**: Browser-stored job information MUST be scoped to the API boundary
  that created it so changing between production, Firebase preview, or local
  deployments cannot expose or falsely restore an unrelated job.
- **SR-009**: Compiled frontend artifacts MUST contain no Tunnel credentials,
  secrets, private addresses, administrator tokens, or embedded temporary API
  URLs.

### Failure and Rollback Behavior

- **FB-001**: If a required internal capability is unavailable, the affected
  request MUST fail safely while unrelated website paths remain unaffected.
- **FB-002**: If path isolation, HTTPS, Tunnel protection, or existing-site
  preservation cannot be proven, production release MUST stop before cutover.
- **FB-003**: If acceptance fails after cutover, the operator MUST be able to
  restore the recorded previous routing and service state through the approved
  rollback procedure.
- **FB-004**: Rollback MUST preserve durable job records and MUST not turn a
  queued, running, failed, or cancelled job into a false completion.
- **FB-005**: After rollback, the operator MUST retest the external hostname,
  unrelated baseline paths, local generation service, and direct-exposure
  boundary before declaring recovery complete.
- **FB-006**: If the stable API is unavailable, both the NT-hosted frontend and
  Firebase preview MUST fail with an understandable unavailable state rather
  than a misleading missing-job or false-success result.
- **FB-007**: Frontend rollback and backend-routing rollback MUST be executable
  independently; neither rollback may capture unrelated website paths or alter
  durable job states.

### Key Entities

- **Mango74 Frontend Boundary**: The exact `/mango74` path and approved child
  paths through which users load and navigate the compiled frontend; it does
  not define the separate stable API origin.
- **Compiled Frontend Artifact**: The reviewed HTML, styles, scripts, and static
  assets deployed to the NT Server or an explicitly non-production preview;
  it contains no AI backend, credentials, model files, or generated assets.
- **Stable API Boundary**: The separate authorized HTTPS origin and public API
  base path `https://mango74-api.mangosgo.com/api/*` through which browser
  requests reach the AI backend via the protected named Tunnel route.
- **Origin Allowlist**: The environment-specific set of exact browser origins
  permitted to read responses from the cross-origin stable API.
- **Preserved Website Route**: A `www.mangosgo.com` path outside Mango74 whose
  pre-deployment behavior must remain unchanged.
- **Generation Job**: One accepted generation attempt with an opaque reference,
  durable lifecycle state, timestamps, safe failure information, and result
  reference when completed.
- **Job Access Credential**: Unguessable access information associated with one
  job and required to recover its state or result after a refresh.
- **Input Asset**: One validated reference image associated with exactly one
  generation job.
- **Generated Asset**: One finalized textured GLB associated with exactly one
  completed job and accessible only through that job's authorized boundary.
- **Deployment Baseline**: The recorded pre-change behavior of local services,
  the existing hostname, preserved paths, exposure boundaries, and job state.
- **Health Report**: A safe operator-facing view that distinguishes public
  routing, NT-hosted frontend, stable API, Tunnel, job, storage, workflow, and
  processing-device readiness.
- **Rollback Record**: Evidence that identifies the deployed state, reason for
  rollback, actions taken, restored state, and post-rollback validations.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In external acceptance testing, the exact Mango74 URL reaches a
  usable generation interface within five seconds at the 95th percentile under
  the documented test conditions.
- **SC-002**: In 100% of redirect tests, `/mango74` reaches `/mango74/` in one
  redirect while preserving HTTPS and the original query string.
- **SC-003**: In the approved route and browser test suites, 100% of required
  NT-hosted pages and assets load under `/mango74/`, and 100% of API operations,
  status requests, cancellations, previews, and downloads use only the
  approved separate stable API boundary.
- **SC-004**: One controlled external production acceptance job submitted from
  the NT-hosted frontend through the approved stable API completes on the real
  AI workflow and returns a previewable and downloadable finalized GLB; the
  preview and download bytes are identical.
- **SC-005**: In ten refresh and deep-link trials across queued, running, and
  completed states, the authorized user recovers the correct job view every
  time without an incorrect not-found response.
- **SC-006**: In five queued-job trials, a user can refresh, cancel their job,
  and confirm that it remains cancelled and never starts processing.
- **SC-007**: Missing-, invalid-, expired-, and cross-job-credential tests
  expose zero job metadata, states, previews, inputs, or outputs.
- **SC-008**: Every preserved non-Mango74 baseline route retains its approved
  status, destination, and content identity after deployment and after
  rollback.
- **SC-009**: Look-alike, malformed, encoded, traversal, and mixed-case path
  tests produce zero unintended Mango74 application matches.
- **SC-010**: External checks confirm that Notebook ports `3000`, `8000`,
  `8080`, and `8188` provide no usable direct application access; only the
  approved Cloudflare Tunnel route reaches the backend.
- **SC-011**: Authorized boundary tests produce zero usable direct-to-Notebook
  application responses outside the approved Cloudflare Tunnel path.
- **SC-012**: The operator identifies the failing frontend, stable API route,
  Tunnel, backend dependency, routing, or processing layer within two minutes
  in every documented failure test.
- **SC-013**: Three controlled project-service restart trials result in zero
  lost, duplicated, or falsely completed accepted jobs.
- **SC-014**: An operator can complete the documented rollback and its required
  verification within 15 minutes without application data migration.
- **SC-015**: Repository and evidence scans find zero committed Cloudflare
  credentials, certificate private keys, job credentials, user inputs, or
  generated private assets.
- **SC-016**: In external acceptance testing, a first-time visitor can load the
  Mango74 interface and submit a valid request without site-wide sign-in, while
  every private job-status and result-access test still enforces its job access
  boundary.
- **SC-017**: Inspection of every NT Server release artifact finds only
  compiled frontend pages, styles, scripts, and static assets and finds zero AI
  backend code, model files, credentials, user inputs, or generated results.
- **SC-018**: In production browser tests, 100% of required preflight and API
  requests from exactly `https://www.mangosgo.com` receive the approved
  cross-origin behavior, while wildcard, look-alike, HTTP-downgraded,
  unexpected-port, `null`, and unapproved-origin tests receive no usable
  cross-origin response.
- **SC-019**: In Firebase preview tests with no authorized API available, 100%
  of submission and restored-job attempts display an understandable unavailable
  state rather than an incorrect "job is no longer available" conclusion.
- **SC-020**: In Firebase preview tests with the exact preview origin explicitly
  enabled, one controlled job completes through the stable API boundary; after
  that test permission is removed, the same origin can no longer use the API.
- **SC-021**: Across one controlled Tunnel interruption and recovery trial, the
  frontend remains available, reports the API interruption accurately, and
  resumes use of the same stable API URL without being rebuilt or redeployed.
- **SC-022**: Inspection of all compiled production frontend references and
  public API responses finds zero localhost, loopback, Notebook, ComfyUI,
  temporary Tunnel, local-path, or secret values.

## Assumptions

- The exact requested production location remains
  `https://www.mangosgo.com/mango74/`, and `mango74` is a path rather than a
  subdomain.
- The production frontend and stable AI API intentionally use different
  browser origins, so the exact production frontend origin
  `https://www.mangosgo.com` requires explicit cross-origin permission at the
  API.
- The existing NT Server is authorized to host the compiled Mango74 frontend;
  its software, owner, deployment interface, and rollback mechanism still
  require operator confirmation.
- The NT Server already has a public IP, but users and compiled frontend
  configuration refer to it only through `https://www.mangosgo.com`; its
  numeric address is neither exposed to users nor embedded in the application.
- The existing website has behavior outside `/mango74` that must be measured
  before change and preserved throughout deployment and rollback.
- The server or platform currently serving `www.mangosgo.com` is unknown and
  must be identified by the authorized administrator before deployment.
- The current development Notebook was observed on 2026-09-08 with local IPv4
  `10.203.152.255` and outbound IPv4 `161.200.189.16`; neither observation
  proves a stable or directly reachable production address.
- `161.200.90.4` was not bound to the current Notebook when inspected and is
  not assumed to identify this Production AI Server.
- The current Notebook with the RTX 5070 is the selected Production AI Server;
  Cloudflare Tunnel allows that role without requiring a directly reachable
  public IP on the Notebook.
- Feature 004 remains the validated functional baseline for job access,
  queueing, cancellation, recovery, GLB preview/download, health, and RTX 5070
  execution.
- The backend network permits outbound connectivity required by `cloudflared`;
  no direct inbound application access to the Notebook is required.
- The production interface remains public without site-wide user accounts;
  each job continues to use its own unguessable access information.
- Firebase Hosting is an optional frontend-only preview and is not the
  production Mango74 host or an AI backend.
- The selected stable API boundary is
  `https://mango74-api.mangosgo.com/api/*`. Its Cloudflare record, certificate,
  and named-Tunnel route remain administrator-controlled external
  configuration; this specification does not itself create them.
- Normal browsers and networks may cache redirects, frontend assets, and stale
  session state, so acceptance includes cache-aware and API-boundary-aware
  validation.
- Constitution 4.0.0 requires the Notebook to be the sole application server,
  identifies `161.200.90.4` as assigned to it, places frontend service behind
  Notebook Nginx, and binds the stable Tunnel route to the Mango74 path. The
  revised NT-hosted frontend and separate-origin API model conflicts with those
  active rules and cannot enter planning until the constitution is amended or
  an approved governance exception explicitly permits the split.

## Dependencies

- Recording the named authorized Cloudflare Zone and NT Server administrators
  before either administrator performs a production change.
- Constitution alignment or an approved exception for the NT-hosted frontend,
  corrected Notebook identity, separate API origin, and revised
  frontend/backend boundary.
- Authorized deployment and rollback access to the NT Server.
- Authorized administrative access to the Cloudflare Zone responsible for the
  stable API hostname and named Tunnel route.
- An administrator-confirmed inventory of the current `www.mangosgo.com`
  origin, preserved routes, and rollback destination.
- A deployment capability that serves `/mango74/` from the compiled frontend
  without capturing unrelated paths, plus a separately authorized stable API route
  that independently reaches the named Tunnel.
- Protected named-Tunnel credentials and an authorized HTTPS API route managed
  outside the application repository.
- The current RTX 5070 Notebook with durable job storage, the approved
  workflow, required models, and ComfyUI.
- A genuinely external network for production acceptance and verification that
  direct Notebook application ingress remains unavailable.

## Out of Scope

- Changing, replacing, or redesigning feature 004 historical artifacts.
- Purchasing or registering another domain or creating an unauthorized public
  hostname.
- Using `https://www.mangosgo.com/mango74/api/*` as the production API boundary
  in this revised cross-origin model.
- Deploying the production frontend at `mango74.mangosgo.com` or another
  unapproved location.
- Altering unrelated `www.mangosgo.com` content, routes, redirects, ownership,
  branding, analytics, or application behavior.
- Deploying FastAPI, ComfyUI, model files, GPU execution, user uploads, or
  generated results to the NT Server or Firebase Hosting.
- Introducing a second AI backend, Edge Server, WireGuard gateway, external job
  queue, cloud database, cloud storage, or cloud GPU.
- Exposing the frontend development port, API port, reverse-proxy port, AI
  workflow port, or GPU-management interface directly to the Internet.
- Selecting `161.200.90.4`, `161.200.189.16`, or another observed address as a
  direct application origin without administrator evidence and architecture
  approval.
- Replacing the current AI model, approved workflow, job lifecycle, output
  format, or generation-quality requirements.
- Granting Cloudflare, DNS, or NT Server privileges to an implementation agent.
- Claiming production readiness before external, security, path-preservation,
  restart, and rollback evidence has passed.
