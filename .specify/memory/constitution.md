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
Public deployment requires owner-approved shared authentication, IP allowlisting,
or VPN access. Upload validation MUST check content, size, and supported format;
user-controlled names and paths are untrusted. Secrets, credentials, private
IPs, and production configuration MUST NOT enter Git.

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

**Version**: 1.0.0 | **Ratified**: 2026-09-02 | **Last Amended**: 2026-09-02
