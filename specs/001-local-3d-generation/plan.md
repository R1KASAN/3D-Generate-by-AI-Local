# Implementation Plan: Local 3D Generation MVP

**Branch**: `001-local-3d-generation` | **Date**: 2026-09-02 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-local-3d-generation/spec.md`

## Summary

Build one private, single-Windows-server web application that accepts a validated
JPEG/PNG image, persists an isolated job in SQLite, dispatches exactly one job at
a time to a pinned ComfyUI/Hunyuan3D shape-and-texture workflow, validates and
atomically publishes the textured GLB, then lets the submitting browser poll,
preview, and download it. macOS development uses the same FastAPI job contract
with a deterministic mock adapter and a known-good textured GLB. Caddy is the
only public listener, provides HTTPS, and passes job-resource requests to
FastAPI for per-job capability-token verification.

## Technical Context

**Language/Version**: Python 3.12 for FastAPI; Node.js 24 LTS, TypeScript 5.x,
Next.js 16.x, and React 19.x for the frontend; separate pinned Python 3.12,
PyTorch (cu128 build), and CUDA 12.8 environment for the Windows ComfyUI
texture lane — amended 2026-09-03 from the original PyTorch 2.6/CUDA 12.6 pin
because the target server's NVIDIA RTX 5070 (Blackwell, `sm_120`) has no
kernel support in PyTorch/CUDA builds older than 12.8; see research.md §5

**Primary Dependencies**: FastAPI, Uvicorn, Pydantic, Pillow, HTTPX, aiosqlite;
Next.js, React Three Fiber 9.x, Three.js, Drei; ComfyUI plus pinned
`kijai/ComfyUI-Hunyuan3DWrapper`; Caddy 2; WinSW stable v2 for Windows services

**Storage**: SQLite on local NTFS with WAL only after a WAL-safe embedded SQLite
version check; isolated local SSD directories per job; no network share

**Testing**: pytest, HTTPX/FastAPI TestClient, Ruff, mypy; Vitest, React Testing
Library, ESLint, TypeScript typecheck, Playwright; adapter contract tests shared
by mock and real adapters

**Target Platform**: macOS development with mocks; Windows 11/Windows Server
production with one NVIDIA RTX GPU; modern desktop browser with WebGL

**Project Type**: Web application with one Next.js frontend, one FastAPI backend,
one backend-owned serial dispatcher, and one local ComfyUI execution engine

**Performance Goals**: Non-GPU status and admission operations remain responsive
under at least two simultaneous users; browser polls every 2 seconds then backs
off to 5–10 seconds; preview interaction targets 30 FPS for the acceptance GLB;
GPU generation time is benchmarked on the target Windows server and is not
claimed before evidence exists

**Constraints**: One active GPU job; exact 10 MiB file limit; 24-hour retention;
reject new jobs below 10% free disk; existing jobs may continue; only HTTPS 443
is the public application entry point, with 80 only for redirect/certificate;
ports 3000, 8000, 8188, and 3389 are never directly public; no token in query
strings or logs; no public deployment before license, domain, network, firewall,
service-account, reboot, and real textured-GLB gates pass

**Scale/Scope**: Private MVP on one machine, one backend process, one dispatcher,
one GPU worker, at least two concurrently submitted jobs, local files only; no
payments, application accounts, Redis, PostgreSQL, containers, microservices,
cloud GPU, object storage, multi-GPU, or autoscaling

## Constitution Check

*GATE: Passed before Phase 0 and re-checked after Phase 1 design.*

| Principle | Design Evidence | Gate |
|---|---|---|
| Smallest Verified Vertical Slice | Mock browser flow precedes Windows GPU, LAN, and public deployment gates | PASS |
| Evidence-Gated Completion | Each phase has automated or explicit manual evidence; Windows claims remain blocked until target tests | PASS |
| Security and Private-Service Boundary | Caddy is the only public listener; internal ports bind to loopback in public deployment | PASS |
| Job and File Isolation | UUID job ID, independent capability token, SQLite ownership metadata, and per-job directories | PASS |
| Single-GPU Queue Correctness | One backend process and serial dispatcher; ComfyUI is an execution adapter, not the durable queue | PASS |
| Replaceable Integration Boundary | Mock and ComfyUI adapters implement one `GenerationAdapter` contract | PASS |
| Cross-Platform Discipline | `pathlib`, environment paths, separate runtime environments, and platform-specific service wrappers | PASS |
| Test-First Critical Behavior | Contract, state, upload, token, isolation, recovery, viewer, and E2E tests are mandatory | PASS |
| Ownership-Critical Decisions | A/A/A decisions are locked; license/domain/service-account decisions gate only public deployment | PASS |
| Scope and Simplicity | One frontend, backend, SQLite database, dispatcher, engine, and local storage | PASS |

### Post-Design Re-check

Phase 1 adds no new infrastructure and does not weaken any gate. The texture
wrapper is a pinned model integration required by the textured-GLB requirement,
not a new service. Public deployment remains explicitly blocked until the owner
accepts the current model-license territory/hosted-service obligations and the
live Windows/network gates pass.

## Architecture and Data Flow

```text
Browser
  -> Caddy HTTPS (no site-wide login)
  -> Next.js :3000
  -> FastAPI /api/v1 :8000 (X-Job-Token for job resources)
  -> SQLite durable job/queue state + isolated local storage
  -> one serial dispatcher
  -> GenerationAdapter
       -> Mock adapter on macOS
       -> ComfyUI 127.0.0.1:8188 on Windows
  -> validate textured GLB
  -> atomic publish
  -> job-token-authorized fetch -> browser object URL -> R3F preview/download
```

The frontend polls persisted FastAPI state; it never connects to ComfyUI. The
real adapter may consume ComfyUI WebSocket events internally, but reconnect and
restart reconciliation always use `/queue` and `/history/{prompt_id}`.

### Access-Control Contract

1. Caddy exposes the public page and `/api/v1` over HTTPS without site-wide
   Basic authentication, while Next.js, FastAPI, and ComfyUI remain private.
2. FastAPI returns one 256-bit random job token once at creation and stores only
   its digest.
3. The browser sends that token in `X-Job-Token` for status, model, and download.
   It MUST NOT use a query parameter. A bootstrap URL fragment may be consumed
   client-side and removed immediately with `history.replaceState`.
4. Missing, invalid, expired, or wrong-job tokens receive the same not-found
   response as an unknown job so job existence is not disclosed.

## Project Structure

### Documentation (this feature)

```text
specs/001-local-3d-generation/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── openapi.yaml
│   ├── generation-adapter.md
│   └── comfyui-workflow-manifest.md
├── checklists/
│   └── requirements.md
└── tasks.md                 # created later by $speckit-tasks
```

### Source Code (repository root)

```text
apps/
├── api/
│   ├── pyproject.toml
│   ├── src/local3d/
│   │   ├── api/
│   │   ├── domain/
│   │   ├── persistence/
│   │   ├── services/
│   │   ├── storage/
│   │   └── adapters/generation/
│   └── tests/{unit,contract,integration}/
└── web/
    ├── app/
    ├── components/
    ├── lib/
    └── tests/{unit,e2e}/
workflows/hunyuan3d/
├── editable/
├── api/
└── workflow-manifest.json
fixtures/
├── inputs/
└── models/sample-textured.glb
deploy/
├── caddy/
├── windows/
└── firewall/
scripts/
├── dev/
├── verify/
└── windows/
storage/                       # runtime only; ignored by Git
```

**Structure Decision**: Keep a small web/backend split matching the PRD. Next.js
runs on port 3000 in production as originally specified; FastAPI runs on 8000;
ComfyUI remains isolated on 8188. Model/runtime assets and Windows deployment
files are kept outside application code so mock development cannot be mistaken
for GPU validation.

## Delivery Gates

1. **macOS mock**: upload, durable job, polling, protected result fetch, viewer,
   download, cleanup, and automated E2E pass with the mock adapter.
2. **Windows shape smoke**: official/native Hunyuan3D 2.1 shape workflow proves
   GPU/runtime basics; this does not satisfy MVP acceptance.
3. **Windows textured GLB**: pinned Hunyuan3D 2.0 wrapper workflow produces a
   non-empty GLB with mesh, UV, material, and texture for two serial jobs without
   OOM. Failure blocks integration; it MUST NOT silently degrade to shape-only.
4. **LAN**: full frontend/backend/real-adapter flow passes on the private network;
   ComfyUI remains inaccessible to LAN clients.
5. **Service/reboot**: restricted service account, headless GPU execution,
   dependency restart, and machine reboot recovery pass.
6. **Public deployment**: owner accepts model-license deployment scope, locks a
   permitted domain/DDNS and authorized-user territory, verifies the retained
   Public IP and no-CGNAT/routing state, forwards only 80/443, validates Caddy and
   firewall, and completes an external-network HTTPS/auth/port test.
