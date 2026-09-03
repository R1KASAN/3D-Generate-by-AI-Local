# Research: Local 3D Generation MVP

**Feature**: `001-local-3d-generation`  
**Date**: 2026-09-02

This document records planning decisions and source-backed constraints. It is
not runtime proof. Windows GPU, LAN, reboot, and public-network claims remain
unverified until their delivery gates produce recorded evidence.

## 1. Single-server application shape

**Decision**: Run one Next.js server on `127.0.0.1:3000`, one FastAPI process on
`127.0.0.1:8000`, and one ComfyUI process on `127.0.0.1:8188`. Caddy is the only
public listener.

**Rationale**: This preserves the owner-approved PRD, keeps deployment on one
Windows GPU machine, and makes the public boundary easy to audit.

**Alternatives rejected**: Static-exporting the frontend would be viable but
would change the stated production shape without an MVP requirement. Docker,
microservices, and cloud hosting add unneeded deployment surfaces.

## 2. Durable queue ownership

**Decision**: FastAPI/SQLite own durable job state and admission order. One
backend dispatcher submits at most one active GPU job to ComfyUI. ComfyUI is the
execution engine, not the only durable source of truth.

**Rationale**: Browser refresh, backend restart, duplicate submissions, and
engine failure require state that survives outside ComfyUI's in-memory queue.

**Alternatives rejected**: Relying only on ComfyUI queue/history cannot express
the complete public job lifecycle safely. Redis is an MVP non-goal.

## 3. Browser progress transport

**Decision**: The browser polls the backend every 2 seconds while state changes,
then backs off to 5–10 seconds. The real adapter may use ComfyUI WebSocket events
internally, but reconciles with `/queue` and `/history/{prompt_id}`.

**Rationale**: Polling is easy to reconnect after refresh and keeps ComfyUI
identifiers and protocol details out of the public API.

**Alternatives rejected**: A public browser-to-ComfyUI WebSocket violates the
private-service boundary. A backend WebSocket can be added only after evidence
shows polling is inadequate.

## 4. Two-layer access control

**Decision**: Caddy shared credentials protect the whole site. Each job receives
a separate 256-bit random capability token sent as `X-Job-Token`; only its digest
is stored. Token comparison is constant-time. Tokens never appear in query
strings, logs, filenames, or persisted browser storage by default.

**Rationale**: Caddy Basic authentication answers “may this person enter the
service?” while the job token answers “may this browser access this job?”. The
custom header avoids conflict because Basic authentication already uses the
standard `Authorization` header. Caddy strips that Basic header before proxying
API requests.

**Alternatives rejected**: Application accounts add registration, recovery, and
role scope. Query tokens leak through history and logs. A single shared password
without job tokens cannot prevent cross-job access.

The university/network authentication exemption in the retained PDF is a
network-connectivity fact only; it does not authenticate this application.

## 5. Hunyuan3D texture lane

**Decision**: The final MVP lane uses Hunyuan3D 2.0 shape plus texture through a
pinned `kijai/ComfyUI-Hunyuan3DWrapper` revision. The audited planning candidate
is commit `2609efa38f6a98292476f714839b7c1e5f9b699a`; it must be revalidated and
recorded in the workflow manifest on the Windows server. Native Hunyuan3D 2.1
shape generation is only an earlier hardware smoke test.

**Rationale**: MVP acceptance requires a textured GLB. The wrapper documents a
Windows-tested Python 3.12 / PyTorch 2.6 / CUDA 12.6 path and exposes the shape,
paint, and mesh export nodes needed by the workflow.

**Amendment (2026-09-03)**: The provisioned Windows server's GPU is an NVIDIA
RTX 5070 (Blackwell, compute capability `sm_120`). PyTorch 2.6 and CUDA 12.6
predate Blackwell consumer support and contain no `sm_120` kernels, so
`torch.cuda` operations would fail even with a healthy driver. The pinned
Python/CUDA environment for the ComfyUI texture lane is updated to PyTorch
(cu128 wheel build) and CUDA Toolkit 12.8 — the first versions with official
Blackwell support — while keeping Python 3.12 unchanged. This must be
revalidated with actual `torch.cuda.is_available()` / `get_device_name(0)`
evidence at T060, same as any other pinned dependency.

**Alternatives rejected**: Treating a shape-only GLB as success would falsify the
acceptance criteria. Auto-updating custom nodes makes results unreproducible.

**Hardware gate**: Published memory figures are planning guidance only. The
target Windows NVIDIA server must produce two serial textured jobs without OOM.

## 6. ComfyUI API and result discovery

**Decision**: Submit API-format workflow JSON to `POST /prompt`; observe `/ws`
internally; reconcile using `GET /queue` and `GET /history/{prompt_id}`. Inject a
server-created output prefix `jobs/<job_id>/model`. After successful execution,
resolve exactly one `.glb` in the job output directory, validate it, then publish
it atomically into application-owned storage.

**Rationale**: The wrapper export node returns a string path and may not expose a
downloadable UI artifact in history. A unique, sanitized server-side prefix and
strict zero/one/many checks prevent stale or cross-job output selection.

**Alternatives rejected**: Searching all of ComfyUI output by newest timestamp is
racy and unsafe. User-supplied output paths are forbidden.

## 7. SQLite safety

**Decision**: Use SQLite on local NTFS, one application process, short write
transactions, a busy timeout, foreign keys, and WAL only after checking that the
embedded SQLite includes the relevant WAL corruption fix (3.51.3 or a documented
backport such as 3.50.7/3.44.6). Otherwise use rollback journal until upgraded.

**Rationale**: SQLite is the owner-selected single-server database. The explicit
version gate avoids blindly enabling WAL on an affected runtime.

**Alternatives rejected**: PostgreSQL adds service administration without an MVP
need. Network-shared SQLite is unsupported for this design.

## 8. Upload, retention, and low-disk admission

**Decision**: Accept only content-verified JPEG or PNG files up to exactly
10 MiB. Stream to a server-named temporary file, enforce a bounded request body,
verify and fully decode with Pillow, then atomically move it into the job folder.
Retain job data for 24 hours from creation. Reject new jobs with HTTP 507 when
free storage is below 10%; already accepted jobs may continue.

**Rationale**: Content verification, server-generated paths, bounded reads, and
per-job folders limit upload and path attacks. Admission control preserves space
without killing expensive active GPU work.

**Alternatives rejected**: Trusting filename extensions or multipart metadata is
unsafe. Deleting active jobs at the threshold creates inconsistent state.

## 9. HTTPS, domain, firewall, and current Public IP

**Decision**: A domain or DDNS name points to the owner-declared current Public
IP at the Public Deployment phase. Only router/firewall ports 80 and 443 reach
Caddy; port 80 is redirect/certificate traffic only. Application and admin ports
remain blocked externally.

**Rationale**: Caddy's normal automatic public certificate flow is domain-based.
The Public IP in the retained project reference is accepted as the current
baseline by owner decision but is not copied into source or runtime configuration.
It must be reverified with CGNAT and router reachability immediately before the
public test.

**Alternatives rejected**: Directly exposing 3000, 8000, 8188, or 3389 violates
the constitution. An IP-only certificate is not the planned production path.

## 10. Windows process lifecycle

**Decision**: Package Next.js, FastAPI, and ComfyUI as restricted Windows services
with WinSW stable v2 where GPU access works. Start in dependency order and verify
reboot recovery. If ComfyUI cannot access the GPU from the service session, use a
documented restricted Task Scheduler login trigger only for that component.

**Rationale**: Services support unattended recovery while the fallback recognizes
that GPU/session behavior must be proven on the target machine.

**Alternatives rejected**: Manually opened terminals are not an operator-verifiable
production procedure.

## 11. Test strategy

**Decision**: Use pytest for domain/API/storage/adapter contracts; Ruff and mypy
for Python checks; Vitest and React Testing Library for frontend behavior; ESLint
and TypeScript checks; Playwright for the browser flow. The mock and real adapter
must run the same contract suite, while real GPU and public-network tests may be
recorded manual gates.

**Rationale**: Critical behavior is test-first while hardware-dependent facts are
not simulated into false completion.

## 12. License and territory gate

**Decision**: Public deployment is blocked until the owner reviews and accepts
the pinned model/workflow licenses, including territory and hosted-service
obligations, and defines the permitted authorized-user territory. Record the
exact license files/hashes in the workflow manifest. This is an operational gate,
not legal advice.

**Rationale**: A private Internet-facing generation service may trigger terms
that do not apply to a purely local experiment.

## Primary sources

Owner-curated, context-specific runtime references are retained in
[`docs/reference/ai-runtime-sources.md`](../../docs/reference/ai-runtime-sources.md).
They are not unpinned installation instructions; the workflow manifest remains
the reproducibility authority.

- [Tencent Hunyuan3D-2](https://github.com/Tencent-Hunyuan/Hunyuan3D-2)
- [Tencent Hunyuan3D-2.1](https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1)
- [ComfyUI Hunyuan3D 2 tutorial](https://docs.comfy.org/tutorials/3d/hunyuan3D-2)
- [ComfyUI-Hunyuan3DWrapper](https://github.com/kijai/ComfyUI-Hunyuan3DWrapper)
- [ComfyUI server routes](https://docs.comfy.org/development/comfyui-server/comms_routes)
- [ComfyUI server messages](https://docs.comfy.org/development/comfyui-server/comms_messages)
- [ComfyUI workflow API format](https://docs.comfy.org/development/api-development/workflow-api-format)
- [FastAPI request files](https://fastapi.tiangolo.com/tutorial/request-files/)
- [FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Next.js App Router](https://nextjs.org/docs/app)
- [React Three Fiber](https://r3f.docs.pmnd.rs/getting-started/introduction)
- [Three.js GLTFLoader](https://threejs.org/docs/#examples/en/loaders/GLTFLoader)
- [Playwright](https://playwright.dev/docs/intro)
- [Caddy automatic HTTPS](https://caddyserver.com/docs/automatic-https)
- [Caddy basic_auth](https://caddyserver.com/docs/caddyfile/directives/basic_auth)
- [Caddy reverse_proxy](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy)
- [Caddy request_body](https://caddyserver.com/docs/caddyfile/directives/request_body)
- [SQLite WAL](https://sqlite.org/wal.html)
- [SQLite transactions](https://sqlite.org/lang_transaction.html)
- [SQLite busy_timeout](https://sqlite.org/c3ref/busy_timeout.html)
