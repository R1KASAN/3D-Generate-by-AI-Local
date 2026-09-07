<!--
Sync Impact Report
- Version change: 1.2.0 -> 2.0.0
- Bump rationale: MAJOR. The former governance permitted a separate public edge
  and direct HTTPS ingress architecture. This version replaces that model with
  one Notebook/PC and an outbound-only Cloudflare Tunnel boundary.
- Modified principles:
  - I. Smallest Verified Vertical Slice + X. Scope and Simplicity
    -> I. Single-Node Architecture
  - III. Security and Private-Service Boundary
    -> II. Outbound-Only Public Connectivity, III. Local Service Isolation,
       and V. Security and Secrets
  - IV. Job and File Isolation + V. Single-GPU Queue Correctness
    -> VI. Reliability and Resource Control
  - II. Evidence-Gated Completion + VIII. Test-First Critical Behavior
    -> VII. Testing and Observability
  - VI. Replaceable Integration Boundary
    -> VI. Reliability and Resource Control
  - VII. Cross-Platform Development Discipline
    -> Development Workflow and Quality Gates
  - IX. Ownership-Critical Decisions + X. Scope and Simplicity
    -> VIII. Scope Control and Governance
- Added principle: IV. Environment Separation.
- Removed standalone principle headings: Smallest Verified Vertical Slice;
  Evidence-Gated Completion; Job and File Isolation; Single-GPU Queue
  Correctness; Replaceable Integration Boundary; Cross-Platform Development
  Discipline; Test-First Critical Behavior; Ownership-Critical Decisions; and
  Scope and Simplicity. Applicable requirements are consolidated above.
- Added sections: none.
- Removed sections: none; both non-governance sections were retained and
  rewritten for the approved architecture.
- Downstream review required: existing specifications, plans, tasks, evidence,
  and operations documents that describe a separate edge server, direct public
  ingress, custom DNS, or a different trust boundary MUST be reconciled before
  their next implementation or deployment use.
- Follow-up TODOs: none.
-->

# 3D Generate by AI Local Constitution

## Core Principles

### I. Single-Node Architecture

The AI Notebook/PC MUST be the sole project server, reverse-proxy host, API
host, ComfyUI host, storage host, and GPU compute node. Its assigned network IP
is `161.200.90.4`. The approved topology MUST NOT contain a separate edge
server, gateway server, cloud compute node, second application server, or
remote GPU worker. Adding any such component requires prior architecture
approval under Principle VIII. One node is the governing constraint because it
matches the available hardware and prevents unsupported operational complexity.

### II. Outbound-Only Public Connectivity

All public access MUST pass through Cloudflare Tunnel. `cloudflared` MUST run on
the Notebook and initiate the connection outbound to Cloudflare; no Internet
client may connect directly to `161.200.90.4`. The architecture MUST NOT require
inbound Internet access to ports `3000`, `8000`, `8080`, or `8188`, and firewall
or routing changes MUST NOT expose those ports publicly. A passing deployment
check MUST demonstrate that the application works through the Tunnel without
direct origin ingress.

### III. Local Service Isolation

Frontend, Caddy, FastAPI, and ComfyUI MUST communicate through loopback or an
explicitly approved private interface. Caddy at `127.0.0.1:8080` is the only
valid Cloudflare Tunnel origin. Caddy routes `/` to the frontend at
`127.0.0.1:3000` and `/api/*` to FastAPI at `127.0.0.1:8000`; FastAPI alone may
invoke ComfyUI at `127.0.0.1:8188`. Public users and browser code MUST NOT call
ComfyUI or other internal services directly. Any change to these bindings or
trust boundaries requires architecture approval.

### IV. Environment Separation

Development and testing MUST use a temporary Cloudflare Quick Tunnel URL and
MUST treat that URL as non-production and potentially public. URL obscurity
MUST NOT be represented as authentication or access control. A stable custom
hostname MAY be configured only after the project receives explicit authority
to use its parent domain. No project activity may purchase a domain, create or
alter external DNS records, or assume domain ownership without explicit owner
approval. Test and future production configuration MUST remain separable so
temporary settings cannot be mistaken for an authorized production endpoint.

### V. Security and Secrets

Tunnel credentials, API keys, tokens, passwords, temporary public URLs, local
environment secrets, private configuration, and user content MUST NOT enter
version control or project-controlled logs. External input MUST be validated
for content, type, size, name, and path before it reaches the AI workflow.
Components MUST run with least privilege, internal services MUST deny direct
public access, and generated files MUST be accessible only through the approved
application boundary. Logs MUST redact sensitive values while retaining enough
context for diagnosis.

### VI. Reliability and Resource Control

Every AI generation MUST have an opaque unique Job ID, isolated input/output
paths, and explicit lifecycle states including queued, running, completed,
failed, and cancelled where supported. Transitions MUST be validated, terminal
states MUST be stable, and restart recovery MUST not silently misreport or
duplicate work. The RTX 5070 execution queue MUST default to one active GPU job
unless target-hardware evidence approves a different bound. Timeouts, retries,
GPU memory, disk usage, upload size, result retention, and cleanup MUST have
documented limits. Startup, shutdown, dependency health, and failure recovery
MUST be reproducible. Mock and real ComfyUI adapters MUST preserve the same
backend-facing job contract.

### VII. Testing and Observability

API contracts, reverse-proxy routing, input validation, job transitions, file
isolation, authorization boundaries, result access, error paths, and recovery
behavior MUST have automated tests where automation is practical. Integration
tests MUST cover the mock AI adapter; hardware- or network-dependent claims
MUST retain a repeatable manual procedure and captured target-environment
evidence. Logs and health endpoints MUST correlate failures by Job ID without
revealing secrets or user content. No task, phase, or release may be marked
complete until its stated validation has passed and evidence has been recorded.

### VIII. Scope Control

Implementation MUST follow the approved specification, plan, and tasks. An
architecture change requires updated design artifacts and explicit owner
approval before application or deployment code changes. Architecture approval
is mandatory for any second server, cloud compute or storage service, public
origin binding, direct inbound rule, custom domain or DNS change, alternate
Tunnel origin, changed service trust boundary, additional GPU node, external
database or queue, or replacement of the reverse-proxy or AI workflow boundary.
Proposals MUST state the need, alternatives, security impact, operational cost,
migration path, and evidence plan. Unapproved complexity remains out of scope.

## Security and Operational Constraints

The only approved public request path is browser to Cloudflare to an
outbound-established Tunnel to Caddy on the Notebook. `161.200.90.4` identifies
the Notebook but MUST NOT be used as a direct public application endpoint.
Internal ports MUST remain unreachable from the Internet. Job outputs MUST be
finalized atomically before download, and inputs, outputs, temporary files, and
logs MUST remain isolated by Job ID. The project MUST document bounded resource
use and recovery from a backend restart, failed workflow, unavailable ComfyUI,
GPU exhaustion, insufficient disk space, missing output, invalid input, and
Tunnel interruption.

Quick Tunnel is authorized only for development and test validation. Any move
to a stable hostname or production exposure requires written authorization for
the parent domain, a reviewed access policy, an updated threat assessment, and
new end-to-end evidence. Authorization to test through Quick Tunnel does not
authorize domain purchase, DNS changes, or a production launch.

## Development Workflow and Quality Gates

Specifications MUST define user value, acceptance scenarios, boundaries, and
measurable outcomes before technical planning. Plans MUST perform a Constitution
Check before and after design and MUST document how the single-node topology,
outbound-only connection, local bindings, resource limits, and security rules
are satisfied. Tasks MUST include exact paths, dependencies, and validation
criteria, with tests preceding critical behavior where practical.

Implementation MUST proceed in independently verifiable phases: local service
health, local reverse-proxy routing, mock AI flow, real ComfyUI/GPU flow, and
Quick Tunnel validation. Local validation MUST precede public test exposure.
Windows-specific process, path, firewall, and service behavior MUST be isolated
and documented; shared application behavior MUST remain portable where the
repository supports another development platform. Reviewers MUST reject work
that bypasses a security, evidence, or architecture gate merely to report
progress.

## Governance

This constitution supersedes conflicting specifications, plans, tasks,
operations documents, and informal practices. Every planning pass, task review,
implementation review, and release decision MUST record a Constitution Check.
Non-compliance blocks only the affected work, but that work MUST NOT proceed
until corrected or covered by an approved exception.

An amendment proposal MUST document its rationale, affected principles and
artifacts, compatibility impact, security and operational risks, migration
steps, validation evidence, and requested semantic-version change. The project
owner MUST approve the amendment before it takes effect. Approved exceptions
MUST identify their scope, owner, expiry or review trigger, and compensating
controls; an exception does not amend this constitution.

Constitution versions follow semantic versioning: MAJOR for incompatible
governance or architecture changes, MINOR for new principles or materially
expanded obligations, and PATCH for non-semantic clarification. The original
ratification date remains fixed, and every amendment records its effective date
as the Last Amended date. The owner is the final authority for architecture
approval and all ownership-critical decisions.

**Version**: 2.0.0 | **Ratified**: 2026-09-02 | **Last Amended**: 2026-09-06
