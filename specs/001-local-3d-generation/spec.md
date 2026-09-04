# Feature Specification: Local 3D Generation MVP

**Feature Branch**: `001-local-3d-generation`

**Created**: 2026-09-02

**Status**: Ready for planning

**Input**: User description: "External users submit an image to a private local 3D-generation service, follow its progress with a per-job token, preview the textured GLB, and download the result through a protected Internet boundary."

## Clarifications

### Session 2026-09-02

- Q: May the retained authentication-exemption memo be used as approval or current Public-IP evidence for this project? → A: No. Its scope is a different Blockchain project; it is historical network context only. Current Public-IP reachability and routing require fresh evidence at the Public Deployment gate.
- Q: How will the MVP authorize public users and isolate job access? → A: The public entry point and job creation do not require a site-wide username/password. Each accepted job receives one cryptographically random access token; that token is required for its status, preview, generated asset, and download. No application user accounts exist in MVP.
- Q: How will the single Windows server persist MVP job state? → A: A local SQLite database; PostgreSQL, replication, and multi-node database operation remain out of scope.
- Q: What upload, retention, and low-disk policy applies to MVP? → A: Accept JPEG and PNG up to 10 MiB, retain job files for up to 24 hours after creation, delete expired files, and reject new jobs below 10% free disk while allowing existing jobs to continue.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Generate and Download a 3D Asset (Priority: P1)

An external user uploads one valid reference image, starts a generation job, receives a unique job reference and token, follows it until it finishes, previews the resulting textured 3D asset, adjusts the view with rotate, zoom, pan, and reset controls, then downloads the same asset.

**Why this priority**: This is the smallest complete user outcome: transform an image into a usable downloadable 3D asset.

**Independent Test**: Using one valid supported image, an evaluator can submit a job, identify it by its job reference and token, reach a completed state, interact with its preview, and download one valid 3D asset without operator help.

**Acceptance Scenarios**:

1. **Given** an external user and a valid supported image, **When** the user submits it for generation, **Then** the service accepts it and returns one opaque job reference and one job token.
2. **Given** a submitted job completes successfully, **When** the user opens its result, **Then** the user can preview the generated asset, reset the view, and download that same asset.
3. **Given** an invalid, corrupt, or oversized image, **When** the user submits it, **Then** the service rejects it before starting generation and explains the problem without exposing internal information.

---

### User Story 2 - Follow Job State and Recover from Failure (Priority: P2)

A holder of a submitted job's token sees whether that job is queued, processing, completed, failed, or cancelled. The user can refresh or reconnect while the job is active and receives a safe, understandable result when processing cannot finish.

**Why this priority**: Generation can take time and fail; transparent state lets users know whether to wait, retry, or seek support.

**Independent Test**: An evaluator submits a job, refreshes during each available non-terminal state, and verifies that the same job state returns. A controlled failure reaches a terminal failed state with a safe message and no result link.

**Acceptance Scenarios**:

1. **Given** a job is waiting or processing, **When** the user refreshes or reconnects, **Then** the service returns the same job reference and current available state information.
2. **Given** processing fails, times out, or produces no usable result, **When** the job reaches a terminal state, **Then** the user sees a safe failure message and cannot download an incomplete asset.
3. **Given** a processing system cannot provide exact queue position or progress, **When** the user checks status, **Then** the service shows only information it can support and does not represent estimates as exact facts.

---

### User Story 3 - Queue Work Without Cross-User Exposure (Priority: P3)

Multiple external users can submit jobs while the single processing resource is busy. Each job waits or processes safely, with isolated input, output, status, and download access.

**Why this priority**: The service must protect user data and keep predictable single-resource behavior before it is shared by more than one user.

**Independent Test**: Two evaluators submit distinct images while one job is active. Each evaluator can see and download only the result covered by their own job token, and no file or status data crosses between jobs.

**Acceptance Scenarios**:

1. **Given** one job is already processing, **When** another user submits a valid image, **Then** the new job waits safely and does not interrupt the active job.
2. **Given** two distinct jobs, **When** either user attempts to access the other job's status, preview, or download, **Then** access is denied without leaking job metadata or files.
3. **Given** duplicate submissions, a restart, or a retry, **When** recovery is attempted, **Then** the service does not overwrite an existing result or attach a result to the wrong job.

---

### User Story 4 - Use the Service Through a Protected Internet Boundary (Priority: P4)

An external user can perform the core flow through HTTPS without a site-wide login, while internal application, processing, storage, and administration interfaces remain unavailable from the Internet. The user must hold the job token to read a particular job's status or result.

**Why this priority**: The product is valuable only when external users can use it without exposing the local server's internal services or another job's data.

**Independent Test**: From an external network, an evaluator completes the P1 flow through HTTPS and separately confirms that non-public service ports are not reachable.

**Acceptance Scenarios**:

1. **Given** an external user, **When** the user opens the service via HTTPS, **Then** the user can complete the P1 flow through the public entry point without a site-wide login.
2. **Given** an external network, **When** an evaluator attempts to reach an internal service or administration interface directly, **Then** the connection is refused or blocked.
3. **Given** a user who lacks a job's access token, **When** that user attempts to read that job's status, preview, or download, **Then** the service refuses access without disclosing whether the job exists.

### Edge Cases

- The processing queue is unavailable or a job is already processing when a valid image is submitted.
- An expected result is absent, incomplete, or unreadable after processing.
- The browser disconnects or refreshes during submission, queueing, processing, preview, or download.
- A server restart occurs while a job is non-terminal.
- A duplicate request, unsafe filename, unsupported file, corrupt image, oversized image, or storage-capacity failure occurs.
- Available disk falls below 10% while a job is processing; new jobs are rejected, but the active job may continue and is monitored for output-write failure.
- A user attempts to guess or reuse another job reference.
- A public-route request succeeds while an internal-port probe is attempted from an external network.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The service MUST permit an external user to submit one supported reference image for 3D asset generation without a site-wide username/password.
- **FR-002**: The service MUST validate every submitted file by supported content, integrity, and approved size before it enters the processing queue.
- **FR-003**: The service MUST create one opaque, unique job reference for every accepted submission and return it to the submitting user.
- **FR-004**: The service MUST represent each job with only these states: queued, processing, completed, failed, or cancelled; every transition MUST be valid and terminal states MUST not change except through a documented recovery process.
- **FR-005**: The service MUST let a holder of the job token retrieve the current state and all available supported progress or queue information for that job after a browser refresh or reconnect.
- **FR-006**: The service MUST create one downloadable textured GLB asset for a successfully completed job and MUST NOT offer an incomplete or missing result.
- **FR-007**: The service MUST provide an interactive result preview that supports rotate, zoom, pan, and reset-view actions before download.
- **FR-008**: The service MUST isolate the input, temporary data, output, metadata, status, preview, and download access of every job.
- **FR-009**: The service MUST reject attempts to access another job's data without disclosing its existence, metadata, content, or storage location.
- **FR-010**: The service MUST process only one generation job at a time unless a later verified processing capability explicitly supports more concurrency.
- **FR-011**: The service MUST present only queue and progress information that it can support; it MUST not state estimates as exact values.
- **FR-012**: The service MUST present safe user-facing messages for invalid input, unavailable processing, timeout, failed generation, missing output, reconnect, duplicate submission, restart recovery, and storage-capacity failure.
- **FR-013**: The service MUST retain enough job history for job-token holders to recover job lookup after refresh and for the operator to recover non-terminal work after a restart.
- **FR-014**: The service MUST provide an operator-verifiable health and recovery procedure that links a job reference through acceptance, queueing, processing, result discovery, and download without exposing user content or secrets.
- **FR-015**: The service MUST expose only the approved HTTPS public entry point to the Internet and MUST block direct Internet access to all internal service, storage, processing, database, and administration interfaces.
- **FR-016**: The public entry point and job creation MUST NOT require a site-wide username/password. Every accepted job MUST receive one cryptographically random access token, and that token MUST be required for the job's status, preview, generated asset, and download. Missing, invalid, expired, or wrong-job tokens MUST not disclose whether a job exists. The retained authentication-exemption memo is neither approval nor current-network evidence for this service. Application user accounts, registration, password recovery, and role management MUST remain out of scope for MVP.
- **FR-017**: The single Windows server MUST persist MVP job metadata and state in one local SQLite database. PostgreSQL, database replication, and multi-node database operation MUST remain out of scope for MVP.
- **FR-018**: The service MUST accept JPEG and PNG input images no larger than 10 MiB; reject all other formats and larger files before queue admission; retain uploads, intermediate artifacts, and generated outputs for no more than 24 hours after job creation; automatically remove expired job files; and reject new jobs when available disk is below 10% of the storage volume. Existing jobs MAY continue processing after new-job admission is disabled, but MUST fail safely if their output cannot be written.

### Key Entities *(include if feature involves data)*

- **Generation Job**: A user-requested 3D-generation attempt with a unique job reference, owner/access scope, state, timestamps, available progress, safe error detail, and result reference when completed.
- **Input Asset**: The validated reference image associated with exactly one generation job.
- **Generated Asset**: The textured GLB result associated with exactly one completed job and accessible only through that job's authorized result path.
- **Job Event**: A time-stamped state, progress, recovery, or failure record used for authorized status recovery and operator traceability.
- **Access Policy**: The owner-approved rule that permits public job submission while reserving status, preview, and download access to the holder of each job's token.
- **Retention Policy**: The owner-approved rule that determines how long inputs, outputs, and job metadata remain available and what happens at storage capacity.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In acceptance testing, 100% of valid test submissions complete the user flow from upload to preview and download or reach a safe, explainable terminal failure state; no job remains indefinitely non-terminal.
- **SC-002**: In the approved input-validation test suite, 100% of invalid, corrupt, unsupported, and oversized test files are rejected before processing.
- **SC-003**: In a two-user concurrency test, 0 input files, status records, previews, metadata records, or downloads are accessible across job boundaries.
- **SC-004**: An evaluator holding the job token can refresh or reconnect during queued and processing states and recover the same job's current state in every documented acceptance scenario.
- **SC-005**: In external-network acceptance testing, users can submit and complete the flow through HTTPS without a site-wide login while probes to every documented internal port fail.
- **SC-006**: An evaluator can rotate, zoom, pan, reset, and download the completed result in every successful-result acceptance scenario.
- **SC-007**: The operator can trace every acceptance-test job from submission to terminal outcome using its job reference without reading the uploaded image or exposing tokens.

## Assumptions

- The service is private and runs on one local server with one processing resource for MVP.
- Development uses representative mock behavior and a sample 3D asset until the target Windows server and GPU are available.
- A valid successful generation creates one textured GLB asset.
- Users have a modern desktop browser and a stable enough connection to retain or recover their job reference.
- Processing duration depends on the target hardware and model; no generation-time service-level target is set until the Windows GPU baseline is measured.
- Payment, billing, user account management, multi-GPU, cloud GPU, Redis, Kubernetes, microservices, object storage, autoscaling, mobile apps, social features, and advanced 3D editing remain out of scope for MVP.
- The owner approved a public entry point without a site-wide username/password,
  with per-job tokens for job resources, local SQLite persistence, and the
  JPEG/PNG 10 MiB, 24-hour retention, 10%-free-disk admission policy for MVP.
- The retained authentication-exemption memo is scoped to a different project.
  It is not deployment approval or current Public-IP evidence for this service.
- The retained Public IP is used only at Public Deployment after Windows GPU/GLB,
  LAN end-to-end, Caddy, firewall, and minimum access-control gates pass. Its
  reachability, routing, static/dynamic status, CGNAT status, domain or DDNS,
  and router forwarding are verified at that gate.
