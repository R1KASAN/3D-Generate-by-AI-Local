<!--
Sync Impact Report
- Version change: 4.0.0 -> 5.0.0
- Bump rationale: MAJOR. The former constitution required the Notebook to host
  both the production frontend and AI backend behind one `/mango74` Tunnel
  route. This amendment moves the compiled frontend to the existing NT Server
  and establishes a separate-origin, stable AI API through a named Cloudflare
  Tunnel to the Notebook.
- Modified principles:
  - I. Single-Node Architecture
    -> I. Single AI Backend Node and Frontend-Only NT Server.
  - II. Outbound-Only Cloudflare Tunnel Connectivity
    -> II. Split Frontend and Stable API Connectivity.
  - III. Local Service Isolation
    -> III. Backend Isolation and Nginx Tunnel Origin.
  - IV. Environment Separation
    -> IV. Production and Preview Separation.
  - V. Security and Secrets
    -> V. Cross-Origin Browser Security and Secrets.
  - VI. Reliability and Resource Control
    -> clarified independent frontend/backend recovery and rollback.
  - VII. Testing and Observability
    -> VII. Testing and Observability, with separate-origin, CORS, NT Server,
       and named-Tunnel evidence gates.
  - VIII. Scope Control
    -> authorizes the NT Server only as a static frontend host and governs
       later boundary changes.
- Added sections: none.
- Removed sections: none.
- Historical artifacts: feature 004 remains unchanged as the record of the
  former Quick Tunnel and Caddy architecture.
- Downstream follow-up required: plan feature 005 against this constitution;
  inventory the NT Server deployment mechanism; validate the authorized API
  hostname, named Tunnel, exact CORS policy, external access, recovery, and
  independent rollback.
- Follow-up TODOs: none.
-->

# 3D Generate by AI Local Constitution

## Core Principles

### I. Single AI Backend Node and Frontend-Only NT Server

The current Notebook containing the RTX 5070 MUST remain the sole AI backend,
application API, Nginx, `cloudflared`, durable job storage, ComfyUI, model,
workflow, generated-output, and GPU compute node. The existing NT Server is an
explicitly approved exception only for serving the compiled static frontend at
`https://www.mangosgo.com/mango74/`. It MUST NOT run FastAPI, ComfyUI, AI
models, workflows, durable jobs, generated outputs, or GPU workloads.

The architecture MUST NOT introduce another backend server, gateway server,
WireGuard node, cloud GPU, external job queue, remote AI worker, or replicated
application runtime without prior architecture approval under Principle VIII.
This boundary keeps AI execution and state on one controlled machine while
allowing the institution's existing web server to publish static files.

### II. Split Frontend and Stable API Connectivity

The approved production frontend path MUST be:

`Public User -> Cloudflare -> NT Server -> /mango74/ static frontend`.

The approved production AI API path MUST be:

`Browser -> https://mango74-api.mangosgo.com/api/* -> Cloudflare -> named
Cloudflare Tunnel -> cloudflared on the Notebook -> Nginx 127.0.0.1:8080 ->
FastAPI 127.0.0.1:8000`.

`cloudflared` MUST establish the Tunnel connection outbound from the Notebook.
The production design MUST NOT require direct inbound Internet access to the
Notebook or use a raw Notebook IP as an application URL. Ports `3000`, `8000`,
`8080`, and `8188` MUST NOT provide direct Internet application access.
Observed private, public, or NAT addresses, including `161.200.90.4`, MUST NOT
be treated as bound or directly reachable on the Notebook without current
network-administrator evidence. The Tunnel design MUST remain independent of a
directly assigned public IP.

### III. Backend Isolation and Nginx Tunnel Origin

Nginx MUST be the production reverse proxy on the AI Notebook and MUST listen
on `127.0.0.1:8080`. It MUST be the only local origin exposed to the named
Cloudflare Tunnel. FastAPI MUST remain on `127.0.0.1:8000`, and FastAPI alone
may invoke ComfyUI on `127.0.0.1:8188`. Public clients and compiled browser code
MUST NOT connect directly to Nginx, FastAPI, ComfyUI, development port `3000`,
private addresses, or public Notebook addresses.

The public stable API MUST preserve the existing `/api/*` FastAPI contract.
Any prefix transformation MUST be explicit, minimal, documented, and tested.
Job creation, status, cancellation, preview, and download MUST use the same
stable API origin. Public responses MUST NOT reveal loopback addresses,
Notebook addresses, ComfyUI URLs, temporary Tunnel URLs, or filesystem paths.

Caddy MAY remain only as a disabled, time-bounded historical rollback artifact
until the Nginx migration and rollback validation are complete. Nginx and Caddy
MUST NOT contend for the same listener.

### IV. Production and Preview Separation

The official production frontend is exactly
`https://www.mangosgo.com/mango74/`; `mango74` is a URL path, not a subdomain.
Requests to `/mango74` MUST redirect safely to `/mango74/`. Static assets,
navigation, refreshes, and supported deep links MUST work below that base path,
and deployment MUST NOT alter any unrelated `www.mangosgo.com` route.

The production AI API is exactly
`https://mango74-api.mangosgo.com/api/*`. Production MUST use an authorized
named Cloudflare Tunnel. Random `trycloudflare.com` Quick Tunnel URLs MAY be
used only for isolated development or acceptance testing and MUST NOT be
embedded, stored, or represented as the production API endpoint.

Firebase Hosting MAY provide a frontend-only preview. It MUST NOT host the API,
ComfyUI, models, workflows, outputs, or GPU workloads, and it MUST NOT replace
the official Mango74 frontend. Preview configuration and access MUST remain
independently removable from production configuration.

### V. Cross-Origin Browser Security and Secrets

Because the production frontend and API have different origins, FastAPI MUST
allow the exact production browser origin `https://www.mangosgo.com` and MUST
reject wildcard, look-alike, HTTP, unexpected-port, unapproved-subdomain, null,
and arbitrary third-party origins. Preflight responses MUST allow only the
methods and headers required by the API contract, including the job-token
header. Cross-origin credentials MUST remain disabled unless a separately
approved cookie-based requirement establishes a need.

The optional Firebase preview origin `https://inw3d-ai-local.web.app` MAY be
enabled only in an explicit test allowlist and MUST be independently revocable.
CORS is a browser policy, not authentication: job tokens, ownership isolation,
rate limits, queue limits, upload validation, resource bounds, and safe errors
remain mandatory regardless of origin.

Cloudflare Tunnel credentials, API keys, tokens, passwords, TLS private keys,
local environment secrets, user uploads, generated outputs, and model files
MUST NOT enter version control, compiled frontend artifacts, or
project-controlled logs. The public API base URL MAY be build configuration but
MUST NOT be treated as a secret. External input MUST be validated for content,
type, size, name, and path before it reaches the AI workflow.

### VI. Reliability and Resource Control

Every AI generation MUST have an opaque unique Job ID, isolated input/output
paths, and explicit lifecycle states including queued, running, completed,
failed, and cancelled where supported. Transitions MUST be validated, terminal
states MUST remain stable, and restart recovery MUST not silently misreport,
lose, duplicate, or falsely complete accepted work. The RTX 5070 queue MUST
default to one active GPU job unless target-hardware evidence approves another
bound.

Timeouts, retries, GPU memory, disk usage, upload size, result retention, and
cleanup MUST have documented limits. Startup, shutdown, dependency health,
Tunnel recovery, and backend recovery MUST be reproducible. A frontend network
failure MUST report API unavailability rather than incorrectly claiming that a
job is missing. Frontend rollback MUST remain independent of backend state and
deployment; backend or Tunnel rollback MUST not change the official frontend
URL unless the public contract itself changes.

### VII. Testing and Observability

API contracts, Nginx routing, CORS allow and deny behavior, frontend base paths,
compiled API configuration, input validation, job transitions, ownership,
result access, error paths, named-Tunnel recovery, and internal-port isolation
MUST have automated tests where practical. Tests MUST distinguish an
unreachable API from a real not-found or expired-job response.

Target-environment evidence MUST prove that the NT Server serves only the
compiled frontend under `/mango74/`, unrelated `www.mangosgo.com` paths remain
unchanged, the stable API reaches Nginx, FastAPI, ComfyUI, and the RTX 5070
through the named Tunnel, and no direct Notebook route provides an application
response. Production completion also requires evidence for exact CORS
behavior, browser refresh and cancellation, protected preview/download,
service and Tunnel restart, durable recovery, and independent frontend and
backend rollback.

Logs and health endpoints MUST correlate failures by Job ID without exposing
secrets, user content, internal addresses, or temporary URLs. No task, phase,
or release may be marked complete before its stated validation has passed.

### VIII. Scope Control

Implementation MUST follow an approved specification, plan, and tasks. Feature
005 design artifacts MUST describe the split frontend/API origins, static-only
NT Server boundary, named Tunnel, loopback services, exact CORS policy, failure
behavior, migration, validation, and rollback before deployment or application
changes begin. Feature 004 specifications, plans, tasks, and evidence MUST
remain unchanged as historical records of the former Quick Tunnel and Caddy
architecture.

Architecture approval is mandatory for another backend runtime, server-side
logic on the NT Server, cloud compute or storage, direct Notebook ingress, any
public internal-service port, an alternate Tunnel origin, a different public
frontend or API origin, wildcard CORS, credentials-based browser sessions, an
external database or queue, an additional GPU node, a replacement reverse
proxy, or a replacement AI workflow. A proposal MUST state the need,
alternatives, security impact, operational cost, migration, rollback, and
evidence plan. Unapproved complexity remains out of scope.

## Security and Operational Constraints

The NT Server deployment package MUST contain only compiled HTML, CSS,
JavaScript, fonts, images, and required static assets. It MUST NOT include
FastAPI, Python environments, ComfyUI, workflows, models, job databases,
uploads, generated outputs, credentials, or private runtime configuration.
Production browser code MUST contain only the authorized stable API base and
MUST NOT contain localhost, loopback, private IPs, public Notebook IPs,
temporary Tunnel URLs, or secrets.

The named Tunnel MUST forward only to Nginx at `127.0.0.1:8080`. Nginx MUST
fail safely for unavailable upstreams, enforce documented upload and timeout
limits, preserve request correlation, and avoid leaking internal details. Job
outputs MUST be finalized atomically before download, and existing job-token
ownership rules MUST protect status, cancellation, preview, and download.

The project MUST document recovery from unavailable FastAPI, unavailable
ComfyUI, GPU exhaustion, queue saturation, insufficient disk, invalid input,
missing output, Nginx failure, `cloudflared` failure, named-Tunnel interruption,
CORS rejection, and NT Server frontend failure. Stopping the Tunnel MUST make
the public API unavailable without creating a direct fallback; restarting it
MUST restore the same stable API URL.

Authorized administrators MUST approve or perform Cloudflare Zone, named
Tunnel, DNS, and NT Server changes through secure processes. Authorization MUST
NOT be represented as possession of account credentials. Existing route and
rollback state MUST be recorded before change, and unrelated
`www.mangosgo.com` routes MUST remain unchanged.

## Development Workflow and Quality Gates

Specifications MUST define user value, both public origins, acceptance
scenarios, browser security, ownership boundaries, failure behavior, and
measurable outcomes before technical planning. Plans MUST perform a
Constitution Check before and after design and show how the static NT Server,
single backend Notebook, named outbound Tunnel, loopback bindings, exact CORS
policy, resource controls, observability, deployment, and rollback comply.
Tasks MUST include exact repository paths, dependencies, validation criteria,
and tests preceding critical behavior where practical.

Implementation MUST proceed in independently verifiable phases: current-state
inventory and backup; static export under `/mango74/`; configurable stable API
base; exact CORS tests; local Nginx and backend validation; named-Tunnel
configuration by an authorized administrator; NT Server deployment; external
browser and real GPU acceptance; interruption and restart recovery; direct
access denial; unrelated-route comparison; and independent rollback. Local and
automated validation MUST precede production routing changes. Reviewers MUST
reject work that bypasses a security, evidence, ownership, or architecture gate
merely to report progress.

## Governance

This constitution supersedes conflicting active specifications, plans, tasks,
operations documents, and informal practices. Feature 004 remains a historical
record but MUST NOT govern feature 005 production deployment. Every planning
pass, task review, implementation review, and release decision MUST record a
Constitution Check. Non-compliance blocks the affected work until corrected or
covered by an approved exception.

An amendment proposal MUST document its rationale, affected principles and
artifacts, compatibility impact, security and operational risks, migration,
rollback, validation evidence, and requested semantic-version change. The
project owner MUST approve the amendment before it takes effect. Approved
exceptions MUST identify their scope, owner, expiry or review trigger, and
compensating controls; an exception does not amend this constitution.

Constitution versions follow semantic versioning: MAJOR for incompatible
governance or architecture changes, MINOR for new principles or materially
expanded obligations, and PATCH for non-semantic clarification. The original
ratification date remains fixed, and every amendment records its effective
date as the Last Amended date. The project owner is the final authority for
architecture approval. Only authorized Cloudflare Zone, Tunnel, DNS, and NT
Server administrators may approve or perform changes in their managed systems.

**Version**: 5.0.0 | **Ratified**: 2026-09-02 | **Last Amended**: 2026-09-09
