# Feature Specification: Single-Node AI Generation with Secure Public Test Access

**Feature Branch**: `main` (no feature branch was created)

**Feature Directory**: `004-secure-ai-test-access`

**Created**: 2026-09-06

**Status**: Ready for planning

**Input**: User description: "Allow public users to access a single-Notebook
AI/3D generation service through a temporary HTTPS test address, submit jobs,
follow job state, retrieve results, and receive safe failure information without
direct Internet ingress or an unauthorized custom domain."

**Supersedes**: The public-access topology and operational assumptions in
feature `003-outbound-tunnel-entry`. Feature `001-local-3d-generation` remains
authoritative for approved generation, job-access, upload, result, retention,
and single-processing-resource behavior unless this specification strengthens
them.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Generate and Retrieve a 3D Asset (Priority: P1)

A public user opens the temporary HTTPS test address, submits one supported
reference image, receives confirmation that the request was accepted, follows
the job until it reaches a terminal state, previews a successful 3D result, and
downloads the finalized asset.

**Why this priority**: This is the smallest complete user outcome and proves
that the project can provide useful AI generation from outside the Notebook's
local network.

**Independent Test**: From an external network, an evaluator can submit one
valid image, retain the returned job access information, observe the job move
through valid states, preview the completed result, and download the same
finalized asset without operator assistance.

**Acceptance Scenarios**:

1. **Given** the public test service is available, **When** a user opens its
   HTTPS address, **Then** the generation interface loads and clearly identifies
   itself as a temporary non-production test service.
2. **Given** a supported valid image, **When** the user submits a generation
   request, **Then** the service accepts it and returns an opaque job reference
   and the access information required to revisit that job.
3. **Given** an accepted job, **When** the user checks it during processing,
   **Then** the service reports one valid current state and only progress
   information it can support accurately.
4. **Given** a successfully completed job, **When** the authorized user opens
   the result, **Then** the user can preview and download the same finalized 3D
   asset.

---

### User Story 2 - Understand and Recover from Job Failure (Priority: P2)

A user receives safe and understandable guidance when input is invalid, the
processing service is unavailable, capacity is exhausted, generation times out,
or a job cannot produce a usable result. Refreshing or reconnecting does not
silently lose or falsely complete the job.

**Why this priority**: AI generation is long-running and failure-prone. Users
must know whether to wait, retry later, correct their input, or contact the
operator.

**Independent Test**: An evaluator induces each documented validation,
capacity, dependency, timeout, missing-result, and reconnect condition and
verifies that every accepted job remains recoverable or reaches a safe terminal
state with no incomplete result exposed.

**Acceptance Scenarios**:

1. **Given** invalid, corrupt, disguised, unsupported, or oversized input,
   **When** the user submits it, **Then** the service rejects it before AI
   processing and explains how to correct the request without exposing internal
   details.
2. **Given** a queued or running job, **When** the browser refreshes or
   reconnects, **Then** the authorized user recovers the same job and its
   current state.
3. **Given** processing fails, times out, is cancelled, or produces no usable
   output, **When** the user checks the job, **Then** the service reports the
   correct terminal state and offers no incomplete download.
4. **Given** the service cannot accept more work, **When** a user submits a new
   request, **Then** the service refuses it safely, explains that capacity is
   temporarily unavailable, and does not disturb accepted jobs.

---

### User Story 3 - Keep Concurrent Users Isolated (Priority: P3)

Multiple public users can submit work while the single processing resource is
busy. Each user can access only the state and result associated with their own
job access information, and queued work does not interrupt the active job.

**Why this priority**: A publicly reachable test service must preserve user
privacy and predictable use of the one available processing resource.

**Independent Test**: Five evaluators submit distinct valid images while one
job is running; at most one job processes at a time, the remaining accepted jobs
wait safely, and no evaluator can discover or retrieve another job's state,
metadata, input, preview, or output.

**Acceptance Scenarios**:

1. **Given** one job is running, **When** another valid request is accepted,
   **Then** the new job enters the queue without interrupting the active job.
2. **Given** two distinct jobs, **When** either user supplies missing, wrong,
   expired, or cross-job access information, **Then** the service reveals
   neither job existence nor private job data.
3. **Given** repeated or duplicate requests, **When** the service handles them,
   **Then** no input, state, or output is overwritten or attached to the wrong
   job.

---

### User Story 4 - Operate and Diagnose the Single-Node Service (Priority: P4)

The project operator can start, stop, monitor, and diagnose the complete service
on the one project Notebook. A restart or component failure produces an accurate
health result and preserves or safely resolves accepted jobs.

**Why this priority**: Public testing is credible only when the operator can
identify the failing layer, recover the service predictably, and distinguish an
outage from a failed generation job.

**Independent Test**: The operator performs a clean start and stop, forces one
failure in each documented service layer, and restarts the Notebook while a job
is queued and while a job is running. The health view identifies each affected
capability, and every accepted job is recovered or moved to an accurate safe
terminal state.

**Acceptance Scenarios**:

1. **Given** the Notebook is ready, **When** the operator starts the service,
   **Then** the operator can verify web access, job handling, AI workflow
   readiness, and processing-device readiness independently.
2. **Given** one internal capability is unavailable, **When** the operator
   checks service health, **Then** the report names the unavailable capability
   without disclosing secrets or user content.
3. **Given** a queued or running job during a controlled restart, **When** the
   service returns, **Then** the job is not silently lost, duplicated, or
   incorrectly reported as completed.
4. **Given** the temporary public route is interrupted, **When** connectivity
   returns, **Then** the operator can restore test access without changing the
   application or opening direct Internet ingress.

### Edge Cases

- The temporary test address changes between service sessions.
- The temporary public route is reachable but one internal capability is not.
- The Notebook loses Internet connectivity while local generation continues.
- The browser disconnects during upload, queueing, running, preview, or download.
- Two submissions arrive at nearly the same time for the one processing slot.
- A duplicate request is received after the first request was accepted but
  before the browser received confirmation.
- A queued or running job exists when the application or Notebook restarts.
- A job is cancelled externally while a user is viewing its status.
- Processing reports completion but the expected result is missing, incomplete,
  corrupt, or unreadable.
- Input has a supported extension but unsupported or malicious content.
- A filename contains traversal sequences, reserved names, or unsafe characters.
- Available storage falls below the admission threshold while a job is running.
- Cleanup overlaps with status, preview, or download access.
- A user guesses a job reference or reuses access information for another job.
- A visitor treats the temporary address as a production endpoint or shares it
  beyond the authorized test audience.
- An external client attempts to connect to the Notebook's assigned address or
  any internal service directly.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The service MUST provide a temporary HTTPS address through which
  an external user can open the generation interface without direct access to
  the Notebook's local network.
- **FR-002**: Every page served through the temporary address MUST identify the
  service as a non-production test environment and MUST NOT present the address
  as a permanent project identity.
- **FR-003**: The service MUST allow a public user to submit one JPEG or PNG
  reference image no larger than 10 MiB for one 3D generation job.
- **FR-004**: The service MUST validate input content, integrity, supported
  format, size, filename, and path safety before admitting a job for processing.
- **FR-005**: Every accepted submission MUST receive one opaque unique job
  reference and one unguessable job access credential.
- **FR-006**: A job access credential MUST be required to retrieve that job's
  status, progress, preview, generated asset, or download.
- **FR-007**: Missing, invalid, expired, or cross-job access information MUST
  reveal neither whether a job exists nor any job metadata or content.
- **FR-008**: The service MUST represent job state as `queued`, `running`,
  `completed`, `failed`, or `cancelled`, and MUST permit only documented valid
  state transitions. An authorized user MUST be able to cancel their own job
  while it is still waiting in `queued`, including after refreshing the same
  browser tab; cancellation MUST be durable and MUST NOT interrupt an active
  GPU job.
- **FR-009**: The service MUST preserve authorized job lookup and the latest
  durable state across browser refresh, browser reconnection, application
  restart, and Notebook restart.
- **FR-010**: The service MUST report only progress and queue information it can
  support accurately and MUST NOT present estimates as exact facts.
- **FR-011**: The service MUST process no more than one generation job at a time
  unless a future approved requirement and measured evidence change that limit.
- **FR-012**: Additional accepted jobs MUST wait safely without interrupting,
  replacing, or corrupting the active job.
- **FR-013**: A completed job MUST provide one finalized textured GLB asset that
  the authorized user can preview and download.
- **FR-014**: The preview MUST support rotate, zoom, pan, and reset actions for
  every valid completed asset.
- **FR-015**: The service MUST NOT expose a missing, partial, corrupt, or
  unfinalized output as a completed result.
- **FR-016**: The service MUST provide safe user-facing outcomes for invalid
  input, unavailable processing, capacity exhaustion, timeout, cancellation,
  failed generation, missing output, reconnect, duplicate submission, low disk,
  and restart recovery.
- **FR-017**: Inputs, temporary files, state, events, previews, and outputs MUST
  be isolated by job so that one user's access cannot reveal another job's data.
- **FR-018**: Job files MUST be retained for no more than 24 hours after job
  creation and MUST be removed automatically after expiry.
- **FR-019**: The service MUST reject new jobs when available storage is below
  10% while allowing already accepted work to continue or fail safely if its
  output cannot be written.
- **FR-020**: The operator MUST be able to determine independently whether the
  web experience, job service, AI workflow, processing device, storage, and
  temporary public route are ready.
- **FR-021**: The service MUST support reproducible operator procedures for
  startup, shutdown, health verification, interruption recovery, and restart
  recovery on the project Notebook.
- **FR-022**: After a restart, every previously accepted non-terminal job MUST
  either resume safely or enter an accurate failed or cancelled state with a
  recorded recovery reason; it MUST NOT disappear, duplicate, or become falsely
  completed.
- **FR-023**: Public test access MUST be established through an outbound-created
  connection from the project Notebook and MUST NOT require direct Internet
  ingress to the Notebook or any internal service.
- **FR-024**: The complete service MUST operate on the single project Notebook;
  the feature MUST NOT depend on a second server, remote processing node, or
  cloud compute resource.
- **FR-025**: The feature MUST NOT purchase or register a domain, configure an
  unauthorized custom hostname, or convert the temporary address into a
  production endpoint.
- **FR-026**: Disabling the temporary public route MUST leave the locally
  operated generation workflow usable and MUST NOT require application data
  migration.
- **FR-027**: Diagnostic records MUST correlate activity by job reference while
  excluding access credentials, secrets, submitted content, and generated
  content.

### Key Entities

- **Generation Job**: One accepted AI/3D generation attempt with a unique
  reference, current state, timestamps, available progress, safe failure detail,
  recovery history, and result reference when completed.
- **Job Access Credential**: Unguessable access information associated with one
  job and required to retrieve its private state and artifacts.
- **Input Asset**: One validated JPEG or PNG associated with exactly one
  generation job.
- **Generated Asset**: One finalized textured GLB associated with exactly one
  completed job and available only through that job's authorized result access.
- **Job Event**: A time-stamped state, progress, failure, cancellation, or
  recovery record used for status continuity and operator diagnosis.
- **Public Test Session**: One temporary, non-production period during which an
  HTTPS address exposes the approved application boundary for evaluation.
- **Health Report**: A safe operator-facing view of readiness and failure across
  the web experience, job handling, AI workflow, processing device, storage,
  and temporary public route.
- **Retention Policy**: The approved 24-hour file lifetime, cleanup behavior,
  and low-storage admission rule applied to generation jobs.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In acceptance testing, 100% of valid test submissions either
  produce a previewable and downloadable finalized 3D asset or reach a safe,
  understandable terminal failure within the configured job timeout.
- **SC-002**: At least 95% of external test-page loads display a usable
  generation interface and its non-production notice within five seconds under
  the documented test conditions.
- **SC-003**: In 100% of accepted-submission tests, the user receives the job
  reference and access information within three seconds, excluding file upload
  transfer time.
- **SC-004**: During documented refresh and reconnect tests, an authorized user
  recovers the same job and sees its current durable state within ten seconds in
  every trial.
- **SC-005**: In a five-user simultaneous-submission test, no more than one job
  is running at any time, all other accepted jobs remain safely queued, and no
  job is overwritten or attached to another user's result.
- **SC-006**: Cross-job, missing-credential, invalid-credential, and expired-
  credential tests expose zero job metadata, inputs, previews, or outputs.
- **SC-007**: In the approved validation suite, 100% of corrupt, disguised,
  unsupported, oversized, and path-unsafe inputs are rejected before AI
  processing begins.
- **SC-008**: Controlled missing-output, timeout, low-storage, dependency-loss,
  cancellation, and restart tests expose zero incomplete assets as completed
  results.
- **SC-009**: After each of three controlled Notebook restart trials, the
  operator obtains an accurate health result within five minutes of network
  readiness, and every accepted pre-restart job is recovered or assigned a safe
  terminal state.
- **SC-010**: An operator can identify the specific unavailable capability in
  each documented forced-failure scenario within two minutes without reading
  user content or exposing secrets.
- **SC-011**: In external-network validation, the complete test journey succeeds
  through the temporary HTTPS address while 100% of direct probes to documented
  internal application interfaces receive no project application response.
- **SC-012**: In repository and diagnostic-log scans using known test values,
  zero job access credentials, service secrets, submitted content, or generated
  content are found.
- **SC-013**: Disabling and restoring temporary public access three consecutive
  times requires no application data migration, no second server, and no direct
  Internet ingress.
- **SC-014**: One hundred percent of reviewed test pages, operator instructions,
  and generated test reports describe the temporary address as non-production
  and make no claim of a permanent custom domain or production uptime.

## Assumptions

- Feature `001-local-3d-generation` provides the existing browser flow, job
  model, local state persistence, serial processing behavior, AI workflow,
  textured GLB preview/download, and approved upload and retention policies.
- The Notebook/PC that runs the AI workflow is the same physical machine that
  serves the project and holds the assigned network identity governed by the
  project constitution.
- The project has one AI processing device and no verified basis for more than
  one active generation at a time.
- The service remains accessible without a site-wide account; per-job access
  credentials protect job status and artifacts.
- Users use a current desktop browser and retain the job reference and access
  information returned after submission.
- Generation duration depends on input, workflow, model, and available hardware;
  the plan establishes the timeout and measured baseline without promising an
  unsupported generation-time service level.
- A changing temporary HTTPS address is acceptable for development and test
  sessions, and the operator communicates the current address to evaluators.
- Temporary public access has no production uptime commitment and may be
  interrupted without activating a paid or unauthorized fallback.
- Payment, billing, user-account management, multi-node execution, cloud GPU,
  autoscaling, geographic redundancy, advanced 3D editing, and social features
  remain outside the MVP.

## Dependencies

- Constitution `2.0.0` is the governing architecture and security baseline.
- The existing feature `001-local-3d-generation` workflow must be available in
  a locally testable state.
- The project Notebook requires working Internet access for each public test
  session and functioning local AI hardware for real-generation validation.
- An external network, such as mobile data, is required for public-boundary
  acceptance testing.
- Required AI models and workflow assets must already be lawfully available to
  the project; this feature does not acquire or replace them.

## Out of Scope

- Purchasing, registering, renewing, transferring, or assuming ownership of a
  domain.
- Configuring a custom hostname or external DNS record without explicit owner
  authorization.
- Representing the temporary test address as a stable or production endpoint.
- Adding a separate edge, gateway, application, storage, database, queue, or AI
  compute server.
- Direct Internet ingress to the Notebook or its internal services.
- Multi-node, multi-GPU, cloud-GPU, or paid-relay scaling.
- Replacing the existing AI model or workflow, changing generation quality, or
  redesigning the core 3D generation journey without a separate specification.
- Claiming legal compliance, public availability, or an uptime commitment not
  established by verified evidence.
