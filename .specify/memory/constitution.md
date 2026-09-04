<!--
Sync Impact Report
- Version change: template → 1.0.0
- Added principles: Smallest Verified Vertical Slice; Evidence-Gated Completion;
  Security and Private-Service Boundary; Job and File Isolation; Single-GPU Queue
  Correctness; Replaceable Integration Boundary; Cross-Platform Development
  Discipline; Test-First Critical Behavior; Ownership-Critical Decisions; Scope
  and Simplicity.
- Added sections: Security and Operational Constraints; Development Workflow and
  Quality Gates.
- Removed sections: none.
- Follow-up TODOs: none.

Sync Impact Report (1.0.0 -> 1.1.0, 2026-09-04)
- Version change: 1.0.0 -> 1.1.0 (MINOR: materially expanded Principle III)
- Amended principles: III. Security and Private-Service Boundary - the
  shared-authentication/IP-allowlisting/VPN mandate for public deployment is
  replaced with an explicit either/or: (a) owner-approved shared
  authentication/IP allowlisting/VPN, or (b) an owner-approved per-resource
  capability-token policy with no site-wide login, provided the token is
  never logged and forwarding/verification is evidenced. Also clarifies that
  a private point-to-point tunnel used solely to reach a mobile compute node
  that is never itself the public entry point (e.g. the edge-to-GPU-worker
  WireGuard link in the public-deployment plan) is an internal binding under
  this principle, not "VPN access to the deployment" - the internal ports it
  carries MUST still never be publicly reachable.
- Rationale: the owner approved a public-entry policy of "no site-wide login,
  per-job X-Job-Token only" on 2026-09-04 (see
  evidence/public-deployment/owner-gate.md), which the prior wording of
  Principle III did not permit. This amendment brings the constitution into
  agreement with that written approval instead of leaving a standing
  contradiction between the two documents.
- Affected artifacts: evidence/public-deployment/owner-gate.md (references
  this version); specs/001-local-3d-generation/tasks.md (T097 constitution
  audit checks against this version); docs/operations/public-cutover.md.
- Follow-up TODOs: none - this is a completed amendment, not a placeholder.

Sync Impact Report (1.1.0 -> 1.2.0, 2026-09-05)
- Version change: 1.1.0 -> 1.2.0 (MINOR: materially expanded Principle III)
- Amended principles: III. Security and Private-Service Boundary - the
  absolute "token is never written to logs" clause is scoped to logs the
  project controls or configures, and a new paragraph recognises that an
  owner-approved TLS-terminating third-party proxy necessarily handles the
  credential in cleartext. That residual exposure is permitted only under
  four conjunctive conditions (written owner approval; provider-side
  credential logging disabled wherever that control exists; the exposure
  recorded in security evidence naming the provider; encrypted AND
  certificate-validated proxy-to-origin hop), and the project is forbidden
  from claiming end-to-end non-logging while such a proxy is in the path.
- Rationale: /speckit-analyze finding N1 against feature
  002-cloudflare-public-entry. The owner selected a proxied public entry on
  2026-09-05 in which Cloudflare terminates TLS at the edge. Under the prior
  absolute wording that architecture could not comply, because the provider's
  logging behaviour is outside project control. Rather than reinterpret the
  principle or ignore the conflict, the clause is scoped to what the project
  can actually govern, and the residual is made explicit, bounded, and
  evidenced. The prohibition on overclaiming is deliberate: the honest
  statement is narrower than the one the old wording invited.
- Affected artifacts: specs/002-cloudflare-public-entry/spec.md (FR-011,
  FR-011a, SC-006, SC-006a); specs/002-cloudflare-public-entry/plan.md
  (Constitution Check); specs/002-cloudflare-public-entry/tasks.md (T009,
  T014, T053); evidence/public-deployment/owner-gate.md;
  evidence/public-deployment/residual-exposure.md (new).
- Follow-up TODOs: none.
-->

# Local 3D Generative AI Server Constitution

## Core Principles

### I. Smallest Verified Vertical Slice

Work MUST advance through independently testable slices: browser mock flow,
sample-GLB viewer, mock backend, local AI validation, API integration, LAN
validation, then protected Internet deployment. MVP work MUST NOT expand into
payment, Kubernetes, Redis, microservices, cloud GPU, multi-GPU, autoscaling,
mobile apps, or object storage. This keeps the product focused on a usable,
verifiable generation loop.

### II. Evidence-Gated Completion

No task, phase, or release MAY be marked complete without recorded verification.
Evidence MUST be appropriate to the work: automated tests, type/lint/build
checks, runtime evidence, or explicit manual verification. Hardware-dependent
claims remain blocked until verified on the target Windows NVIDIA server; task
checkboxes and historical documents alone are not evidence.

### III. Security and Private-Service Boundary

HTTPS on port 443 is the sole Internet-facing application entry point; port 80
is permitted only for redirect or certificate issuance. Frontend, backend, AI
workflow engine, database, and remote-administration ports MUST NOT be publicly
reachable. Browsers MUST call the backend only, never the AI workflow engine.
Public deployment requires one of the following, owner-approved in writing:
(a) shared authentication, IP allowlisting, or VPN access; or (b) a
per-resource capability-token policy with no site-wide login, where the
token is never written to any log the project controls or configures, and
its issuance/verification behavior is evidenced (e.g. uniform 404 for
missing/wrong tokens). "Controls or configures" covers every log produced
by a project-operated component - reverse proxy, application, and any
project-run intermediary - and also any third-party log whose content the
project can suppress through available configuration; where such a control
exists the project MUST use it.

An owner-approved third-party proxy that terminates TLS at the network edge
necessarily processes the capability token in cleartext in order to forward
it. This is a recognised residual exposure, not a violation of the clause
above, provided ALL of the following hold: the proxy is owner-approved in
writing; credential logging is disabled wherever the provider exposes that
control; the residual exposure is recorded in the project's security
evidence, naming the provider and what it can observe; and the connection
from that proxy to the origin is both encrypted and certificate-validated.
The project MUST NOT claim the token is unlogged end-to-end while such a
proxy is in the path - it may claim only that no project-controlled log
contains it, and MUST state where the boundary of that claim lies. A
private
point-to-point tunnel used only to let a public-facing edge reach a
non-public compute node (never itself exposed as the public entry point) is
an internal binding, not "VPN access to the deployment," under this
principle - the ports it carries MUST still never be publicly reachable, and
its own address scope MUST stay as narrow as the specific peer it connects,
never a wide allowlist or a full-tunnel default route. Upload validation
MUST check content, size, and supported format; user-controlled names and
paths are untrusted. Secrets, credentials, private IPs, and production
configuration MUST NOT enter Git.

### IV. Job and File Isolation

Each generation MUST use an opaque, unique Job ID. Inputs, outputs, temporary
files, logs, and result access MUST be isolated by that ID. No user may access
another job's content, progress, metadata, or output. State transitions MUST be
explicit and validated; terminal states are immutable except through a documented
recovery operation.

### V. Single-GPU Queue Correctness

The MVP operates one serial GPU execution queue. Multiple users may submit jobs,
but execution concurrency MUST never exceed the verified GPU capability. Queue
position is informational and MUST NOT claim precision unavailable from the
underlying engine. Duplicate submissions, retries, restarts, timeouts, and
AI-engine failures MUST fail safely without producing conflicting results.

### VI. Replaceable Integration Boundary

The backend MUST own a stable job-service interface. Mock and real AI generation
MUST satisfy the same backend-facing contract. Internal workflow details and
engine identifiers MUST NOT leak through the public frontend API. Workflow files,
model versions, and runtime compatibility checks MUST be versioned and
reproducible.

### VII. Cross-Platform Development Discipline

Shared application behavior MUST work in macOS development and Windows
production where applicable. Paths, process execution, environment variables,
and file locking MUST NOT assume POSIX-only behavior. Platform-specific setup
MUST be isolated and documented so the production machine can be reproduced.

### VIII. Test-First Critical Behavior

API contracts, job transitions, upload validation, path isolation, authorization
boundaries, and result access require tests before implementation is considered
complete. Integration tests MUST cover the mock adapter. When real AI or
public-network validation cannot be automated, the project MUST retain a clear
manual verification procedure and captured evidence.

### IX. Ownership-Critical Decisions

Architecture, database choice, public access control, retention policy, upload
limits, and deployment exposure require owner approval. Automation may recommend
defaults but MUST NOT silently decide them. An unresolved decision blocks only
the affected phase; unrelated, safe work may continue.

### X. Scope and Simplicity

MVP defaults to one frontend, one backend, one AI workflow engine, one GPU worker,
and local storage. A new infrastructure component requires a documented product
need, trade-off, and verification benefit before adoption. Simplicity is the
default because it reduces operational risk on the single Windows server.

## Security and Operational Constraints

All public routes, internal bindings, firewall rules, upload limits, storage
retention, job ownership, and recovery behavior MUST be defined before public
deployment. Job outputs MUST be finalized atomically before preview or download.
Logs MUST correlate activity by Job ID without recording secrets or uploaded
content. The project MUST document recovery from a backend restart, a failed
workflow, missing output, insufficient disk space, and unsupported input.

## Development Workflow and Quality Gates

Specifications define user value and acceptance criteria before technical plans;
plans must include a Constitution Check before and after design. Tasks MUST have
clear paths, dependencies, and verification criteria. Implementation proceeds by
phase and records evidence before task completion. Windows GPU, LAN, router, DNS,
certificate, firewall, and public-access work require actual target-environment
evidence and any required owner approval. No implementation step may bypass a
security or quality gate merely to report progress.

## Governance

This constitution governs all project specifications, plans, tasks, implementation,
and reviews. Every plan and implementation review MUST check compliance with these
principles. Exceptions require a documented reason, risk, owner approval, and
review trigger. Amendments MUST record their rationale, affected artifacts, and
semantic-version change: MAJOR for incompatible governance changes, MINOR for new
or materially expanded principles, and PATCH for clarifications only. The owner
is the final authority for all ownership-critical decisions.

**Version**: 1.2.0 | **Ratified**: 2026-09-02 | **Last Amended**: 2026-09-05
