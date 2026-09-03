# Runbook: Windows NVIDIA AI Server — Hardware Gate to Public Deployment (Phase 7–12)

**Owner:** Windows Server Operator; opening public access always requires passing the T085 owner-approval gate first | **Frequency:** As needed, once per server build | **Last Updated:** 2026-09-03 | **Last Run:** Not yet run

**Document version:** 3.0 | **Source language:** Thai | **Thai source:** [windows-ai-server-runbook.th.md](windows-ai-server-runbook.th.md), version 3.0

> This is a repeatable operational guide for Phase 7 through Phase 12. Writing or reading it is not evidence that Windows, an NVIDIA GPU, ComfyUI, Hunyuan3D, a GLB, the LAN flow, or public deployment has passed. Evidence must come from real runs on the target machine.

## Purpose

Take the Windows NVIDIA server from "bare machine" to "AI server genuinely usable by outside users over HTTPS", passing each gate in order:

| Phase | What must be proven | Tasks |
|---|---|---|
| 7 | The pinned runtime can execute a native shape smoke test | T058–T064 |
| 8 | FastAPI talks to real ComfyUI through the same adapter contract as the mock | T068, T072–T074 |
| 9 | A **real textured GLB** is produced and jobs stay isolated | T075–T079 |
| 10 | The full web flow works from a **second device on the LAN** | T080–T084 |
| 11 | HTTPS opens to the public after Owner approval, with two-layer auth | T085–T092 |
| 12 | External-network testing plus the final project-closing audit | T093–T097 |

Stop immediately when any task is FAIL or BLOCKED. Never skip a gate merely to report progress. **Phase 11 carries a special condition**: it requires explicit, written Owner approval before touching any public infrastructure (see T085) — this is a standing condition of the phase, not an ordinary checklist item.

## Hardware boundary (mandatory — read before anything else)

**The machine running the AI server must be Windows with an NVIDIA GPU. No exceptions.**

| Machine | Role | What it may and may not do |
|---|---|---|
| Windows + NVIDIA GPU | **The real AI server** | Runs ComfyUI, Hunyuan3D, FastAPI, GPU generation, and all LAN services — every piece of Phase 7–10 evidence must come from this machine |
| macOS (the Owner's MacBook) | **Development only** | Writing code, running the mock adapter, running non-GPU tests — **must never act as the AI server, and mock results must never substitute for Windows evidence** |

Reason: the MacBook has no NVIDIA GPU or CUDA, so it cannot run Hunyuan3D for real. Passing results from macOS belong to the mock lane (Phase 6, already closed) and are not evidence for this hardware gate.

If anyone proposes running the AI server on macOS, or using macOS results to close a Phase 7–10 task, refuse and report `BLOCKED`.

## Network boundary (important for Phase 11)

Phase 11 opens ports 80/443 to the Internet through **the Windows operator's own router**, not the Owner's router.

- The operator must consent to forwarding ports on their own home/office network — this is the operator's decision as the owner of that network, not something the Owner can simply order.
- If the operator is not comfortable exposing their own router to the public, they must say so to the Owner **before** starting T085. There are alternatives the constitution also permits (such as VPN access).
- The domain/DDNS used will point at the operator's network IP only — no service is relocated to a different machine.

## Source of truth

Read these before changing files or installing software:

- [Constitution](../../.specify/memory/constitution.md)
- [Specification](../../specs/001-local-3d-generation/spec.md)
- [Plan](../../specs/001-local-3d-generation/plan.md)
- [Tasks](../../specs/001-local-3d-generation/tasks.md)
- [Research decisions](../../specs/001-local-3d-generation/research.md)
- [Quickstart and gates](../../specs/001-local-3d-generation/quickstart.md)
- [AI runtime source register](../reference/ai-runtime-sources.md)
- [GenerationAdapter contract](../../specs/001-local-3d-generation/contracts/generation-adapter.md)
- [Workflow-manifest contract](../../specs/001-local-3d-generation/contracts/comfyui-workflow-manifest.md)

When an external video or README conflicts with these artifacts, the project artifacts and owner-approved decisions govern.

## Scope boundary (read before starting)

**In scope for this runbook:** Phase 7 → 8 → 9 → 10 → 11 → 12 in order, ending with an external user genuinely able to use the app over HTTPS.

**Out of scope — do not do these, even after Phase 11-12 pass:**

| Topic | Status | Reason |
|---|---|---|
| SDXL re-texturing / ControlNet texture projection | Post-MVP quality lane | Reference only. Never add to the MVP workflow, dependencies, or task completion criteria. |
| Blender retopology, Quad Remesher, texture painting, texture baking | Post-MVP quality lane | Manual post-MVP work, not part of the FastAPI/ComfyUI pipeline. |
| Changing access control away from "shared Caddy credential + per-job token" | Requires a fresh Owner decision | [tasks.md T085](../../specs/001-local-3d-generation/tasks.md) locks in this approved decision. Changing it supersedes an owner decision and needs written re-approval — never change it unilaterally. |
| Opening anything to the public before the T085 owner-approval gate passes | Always stop | See "Phase 11 — T085" below. This condition has no exceptions. |

**About the Public IP:** it is not a secret, but avoid typing the raw number into chat/LINE — record it in `evidence/public-deployment/dns-router.md` (redacted as T089 requires) and let the Owner view it from the evidence file or the repo instead.

**Values that must not become requirements:** tuning numbers found in external videos or tutorials — such as `steps=100`, octree resolution `900–1000`, or a face count of `1,000,000` — are **experimental values**, not MVP requirements. Prove them against the real machine's VRAM and record the values actually used in the manifest.

**CUDA 12.6** is a planning candidate consistent with the wrapper, but never install it blindly from a video. It must pass T058–T060 and be pinned in the manifest first.

**Status of external videos and tutorials:** *reference only*, per the [source register](../reference/ai-runtime-sources.md). They never substitute for real Windows evidence and never close a task.

## ComfyUI API integration rules

These rules apply from Phase 7 onward and remain binding in every later phase.

**Permitted path:**

```text
Browser
  -> FastAPI only
      -> upload image safely
      -> create opaque Job ID + isolated directory
      -> map allowed API-workflow fields
      -> POST /prompt to 127.0.0.1:8188
      -> observe /ws, /queue, /history
      -> validate exactly one GLB
      -> publish controlled result to application storage
      -> browser preview/download
```

**Strictly forbidden:**

```text
Browser -> ComfyUI directly
User filename/path -> workflow output path
Shared ComfyUI input/output without Job ID prefix
overwrite=True on shared input directory
Search newest output file
Automatic resubmit after timeout/restart
Expose :8188, :8000, :3000, or :3389 publicly
```

Only **API-format** exported workflows may be used (not the regular workflow file), and ComfyUI prompt IDs must never leak into public API models.

## Prerequisites

- [x] The Owner has confirmed the GitHub destination: [`R1KASAN/3D-Generate-by-AI-Local`](https://github.com/R1KASAN/3D-Generate-by-AI-Local), visibility `public` — the baseline is pushed (see Step 0).
- [ ] The target machine is **Windows with an NVIDIA GPU**, not macOS (see Hardware boundary).
- [ ] The operator has local-administrator access only when a pinned installer requires it.
- [ ] The operator can write to the project root, evidence directory, and local runtime directory.
- [ ] The PC has sufficient free disk for manifest-defined runtime/model assets.
- [ ] ComfyUI, FastAPI, and browser services are not Internet-facing before Phase 11; ports `3000`, `8000`, `8188`, and `3389` remain private at all other times.
- [ ] The operator has read every Source-of-truth artifact.
- [ ] (For Phase 11) The operator consents to forwarding ports 80/443 on their own router, or has told the Owner before T085 if that is not comfortable.

## Procedure

### Step 0: Clone and verify the Git baseline on the Windows machine

> **Status: the baseline is already created and pushed.** The operator does not create a new commit or repository. This step is to *fetch and verify* that the Windows machine has exactly the source the Owner reviewed.

| Item | Value |
|---|---|
| Repository | [`R1KASAN/3D-Generate-by-AI-Local`](https://github.com/R1KASAN/3D-Generate-by-AI-Local) |
| Visibility | `public` (Owner confirmed) |
| Default branch | `main` |
| Baseline scope | source/spec/docs — passed secret review; no model weights, runtime artifacts, or credentials |

Clone on the Windows machine:

```powershell
Set-Location <PARENT_DIRECTORY>
git clone https://github.com/R1KASAN/3D-Generate-by-AI-Local.git
Set-Location 3D-Generate-by-AI-Local
git log -1 --format=%H
git status --short
```

**Expected result:** the commit matches the one the Owner announced, and `git status --short` is empty.

**If it fails:** stop as `BLOCKED`, save sanitized command/error evidence to `evidence/setup/git-baseline.md`, and request Owner confirmation of the repository or access. Never create a new repository or a new baseline commit.

Create local environment files from the templates (real `.env` files are ignored and must never be committed):

```powershell
Copy-Item .env.example .env
Copy-Item apps\api\.env.example apps\api\.env
Copy-Item apps\web\.env.example apps\web\.env
```

**Expected result:** local `.env` files exist and `git status --short` is still empty, confirming `.gitignore` works.

**If it fails:** if any `.env` appears in `git status`, stop immediately and notify the Owner. Do not commit.

#### Before any future commit (standing rule)

Whenever the operator commits new evidence or scripts, scan first. Never use unreviewed `git add .`. Do not commit real `.env` files, credentials, password hashes, tokens, private keys, production/public IPs, router configuration, model weights, ComfyUI output/temp, local storage, logs, caches, or `node_modules`.

```powershell
git status --short
rg -n --hidden --glob '!node_modules/**' --glob '!.git/**' --glob '!*.pdf' `
  '(?i)(api[_-]?key|secret|password|token|-----begin .*private key-----)' <PATHS_TO_STAGE>
git add <REVIEWED_PATHS_ONLY>
```

**Expected result:** no secret and no runtime artifact enters the commit.

**If it fails:** remove the sensitive material, move it into an ignored `.env`, and scan again. Do not commit or push until clean.

---

## Phase 7 — Windows compatibility gate (T058–T064)

### Step 1: T058 — Hardware/runtime inventory

Create and run `scripts/windows/capture_gpu_baseline.ps1` per task T058, then save sanitized output to `evidence/windows/gpu-baseline.md`.

```powershell
nvidia-smi
py -3.12 -c "import platform; print(platform.platform())"
py -3.12 -c "import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0)); print(torch.cuda.get_device_properties(0).total_memory)"
py -3.12 -c "import sqlite3; print(sqlite3.sqlite_version)"
Get-PSDrive -PSProvider FileSystem
```

**Expected result:** real Windows version, GPU model, driver, VRAM, Python, PyTorch, CUDA availability, SQLite version, and disk capacity are captured.

**If it fails:** do not install or change versions at random. Record the missing or mismatched component and stop as `BLOCKED`.

### Step 2: T059 — Install and pin ComfyUI/custom nodes

Use the [runtime source register](../reference/ai-runtime-sources.md) for installation guidance, but select revisions, packages, models, and nodes only from the reviewed workflow manifest.

- Bind ComfyUI to loopback, e.g. `127.0.0.1:8188`
- Record commit/hash/version/license for ComfyUI, the wrapper, custom nodes, and model files
- Never let ComfyUI Manager update nodes unattended
- Restart, then check health from localhost only

```powershell
Invoke-WebRequest http://127.0.0.1:8188/object_info -UseBasicParsing
```

**Expected result:** ComfyUI responds on loopback and revisions/hashes match the manifest.

**If it fails:** stop before T060. Record the exact mismatch without exposing paths or user credentials, then fix the manifest or runtime per the Owner's decision.

### Step 3: T060 — PyTorch/CUDA/native wheel compatibility

Create and run `scripts/windows/verify_hunyuan_runtime.ps1` per task T060. Never auto-upgrade dependencies just to make an import succeed.

```powershell
py -3.12 -c "import torch; assert torch.cuda.is_available(); print(torch.version.cuda); print(torch.cuda.get_device_name(0))"
```

**Expected result:** the Python environment actually used can import the required packages, CUDA is available, the intended GPU is selected, and no version drifts from the manifest.

**If it fails:** record installed versions and sanitized errors in `evidence/windows/runtime-compatibility.md`, then stop as `BLOCKED` and request an Owner decision before changing any dependency.

### Step 4: T061 — Native Hunyuan3D 2.1 shape smoke

Export both the editable and API-format workflows to the paths named in T061, submit through the API, and capture a parseable shape artifact.

**Expected result:** the shape smoke passes with evidence in `evidence/windows/shape-smoke.md`.

**If it fails:** capture the workflow hash, node/version mismatch, and safe error text. A GUI-only success never counts as an API pass.

> A shape-only artifact is not a textured GLB and does not unlock MVP acceptance.

### Step 5: T062 — Manifest/hash and `/object_info` verification

Create and run `scripts/verify/verify_comfy_manifest.py` per task T062, along with the deliberate mismatch fixtures the task defines.

**Expected result:** the pinned runtime passes; a missing/changed node or a hash mismatch fails closed.

**If it fails:** stop before T063 and record the mismatch in `evidence/windows/object-info-check.md` without guessing at version changes.

### Step 6: T063 — Windows GPU validation checklist

Create [windows-gpu-validation.md](windows-gpu-validation.md) per task T063 and fill in every prerequisite with command output, artifact paths, and a `PASS`, `FAIL`, or `BLOCKED` verdict.

**Expected result:** no checklist item is skipped and every result cites real evidence.

**If it fails:** state the smallest blocker and the Owner action required.

### Step 7: T064 — Issue the Phase 7 gate verdict

Create `evidence/windows/phase-7-gate.md` in this format:

```text
Gate: Phase 7 — Windows ComfyUI and Hunyuan3D Compatibility
Date/time and operator:
Host/environment:
Pinned revisions/hashes:
Tasks T058–T063 and evidence links:
Verdict: PASS | FAIL | BLOCKED
Blocker and smallest owner action:
```

**Expected result:** PASS only when T058–T063 all pass; otherwise record FAIL or BLOCKED honestly.

**If it fails:** do not continue to Phase 8, LAN, or public deployment.

---

## Phase 8 — FastAPI-to-ComfyUI adapter (T068, T072–T074)

> Enter this phase only when `evidence/windows/phase-7-gate.md` = PASS.

**Goal:** replace the mock adapter with the real one behind the same contract, without leaking ComfyUI protocols or IDs to the frontend.

### Step 8: T068 — Hardware-gated adapter smoke test

Create `apps/api/tests/integration/test_comfy_adapter_smoke.py` per task T068.

**Expected result:** test collection passes on macOS with a documented skip, and on the Windows machine it fails at the expected assertion (adapter/runtime not yet present).

**If it fails:** never weaken the test to make it pass. Record the real error and stop.

### Step 9: T072 — Implement the real adapter

Create `apps/api/src/local3d/adapters/generation/comfy.py` per task T072.

```powershell
$env:GENERATION_ADAPTER="comfy"
uv run --project apps/api pytest apps/api/tests/contract/test_generation_adapter.py
```

**Expected result:** the same adapter suite passes for both mock and comfy, without returning prompt IDs through any public model.

**If it fails:** never loosen the contract to make it pass. Stop and report the mismatch.

### Step 10: T073 — Manifest verification and fail-closed readiness

Modify `apps/api/src/local3d/adapters/generation/factory.py` and `apps/api/src/local3d/main.py` per task T073.

**Expected result:** mock tests stay green, and when the real manifest is invalid `/api/v1/health/ready` returns a safe 503 (no paths or internal detail exposed).

**If it fails:** never let readiness pass with a mismatched manifest — it must always fail closed.

### Step 11: T074 — Real integration smoke test

```powershell
$env:RUN_COMFY_INTEGRATION="1"
uv run --project apps/api pytest apps/api/tests/integration/test_comfy_adapter_smoke.py
```

Save sanitized request/result evidence to `evidence/windows/comfy-adapter-smoke.md`.

**Expected result:** it passes with ComfyUI bound to loopback only.

**If it fails:** capture the sanitized error and stop before Phase 9.

---

## Phase 9 — Real textured-GLB validation (T075–T079)

> This is the phase that proves the MVP's actual deliverable, not just a shape.

### Step 12: T075 — Run the full shape+texture workflow

Pin and run the workflow at `workflows/hunyuan3d/editable/hunyuan3d-textured-glb.json` and `workflows/hunyuan3d/api/hunyuan3d-textured-glb.json`.

**Expected result:** one API-submitted job creates **exactly one** non-empty GLB, with evidence in `evidence/windows/textured-generation-1.md`.

**If it fails:** record the workflow hash, node error, and VRAM used. On OOM, reduce only within values the manifest permits and record the values actually used — never reduce the acceptance criterion.

### Step 13: T076 — Validate the real GLB

```powershell
python scripts/verify/validate_glb.py <GLB_PATH>
```

Record mesh, primitive, UV, material, texture, size, and SHA-256 data in `evidence/windows/textured-glb-validation.md`.

**Expected result:** every required property passes.

**If it fails:** a GLB without texture or UV data is never a pass. Stop and report.

### Step 14: T077 — Two serial jobs and isolation check

**Expected result:** both GLBs pass validation, stay isolated from each other, and the maximum active GPU job count equals 1 — with Job IDs, hashes, duration, peak VRAM, and overwrite checks recorded in `evidence/windows/two-job-serial.md`.

**If it fails:** if jobs bleed into each other or concurrency exceeds 1, stop immediately. This is an isolation defect that must never be skipped.

### Step 15: T078 — Recovery matrix

Run `scripts/windows/run_recovery_matrix.ps1` covering engine failure, timeout, disconnect, missing output, backend restart, and ComfyUI restart.

**Expected result:** `evidence/windows/recovery-matrix.md` shows safe terminal/reconciled states and **zero duplicate executions**.

**If it fails:** any auto-resubmit or duplicated work is a violation of the ComfyUI API integration rules. Stop.

### Step 16: T079 — Issue the Phase 9 gate verdict

Create `evidence/windows/phase-9-gate.md` with the pinned revision/hash set.

**Expected result:** PASS when T075–T078 all pass, and shape-only evidence is never used as textured completion.

**If it fails:** do not continue to Phase 10.

---

## Phase 10 — LAN end-to-end delivery (T080–T084)

> Completing this phase means the Owner can genuinely start using the AI server and web app over the LAN.

### Step 17: T080 — Windows services

Create `deploy/windows/services/api.xml`, `web.xml`, and `comfyui.xml` (WinSW) with loopback bindings, then run `scripts/windows/verify_services.ps1`.

**Expected result:** `evidence/lan/service-startup.md` records restricted identities, dependency order, healthy services, and a successful real generation after the services are running.

**If it fails:** never bind a service to 0.0.0.0 to make it work. Stop and report.

### Step 18: T081 — Reboot recovery

Run `scripts/windows/verify_reboot_recovery.ps1`.

**Expected result:** `evidence/lan/reboot-recovery.md` proves automatic startup after reboot, state reconciliation, and a new successful job **without manually opening any terminal**.

**If it fails:** if a terminal has to be opened by hand, it is not a pass.

### Step 19: T082 — LAN full flow from a second device

Create and execute the checklist at `docs/operations/lan-acceptance.md`.

**Expected result:** a second LAN device completes upload → queued/processing → textured preview (rotate/zoom/pan/reset) → byte-identical download, recorded in `evidence/lan/full-flow.md`.

**If it fails:** record exactly where the flow broke and stop.

### Step 20: T083 — LAN security checklist

Create `docs/operations/lan-security-checklist.md` and run `scripts/verify/test_lan_boundary.py`.

**Expected result:** `evidence/lan/isolation-and-ports.md` proves cross-job access is denied and that **ports 8000 and 8188 are unreachable from the LAN client**, while the approved LAN entry path still works.

**If it fails:** if 8000 or 8188 is reachable from the LAN, stop immediately. This security boundary must never be relaxed.

### Step 21: T084 — Issue the Phase 10 gate verdict

Create `evidence/lan/phase-10-gate.md` with commands, timestamps, Job IDs, logs, screenshots, and GLB hashes.

**Expected result:** PASS when T080–T083 all pass.

**If it fails:** report BLOCKED with the smallest blocker.

---

---

## Phase 11 — Protected Caddy HTTPS deployment (T085–T092)

> Enter this phase only when `evidence/lan/phase-10-gate.md` = PASS **and** T085 (the owner-approval gate) has been approved. Never touch domain/DNS/Caddy/firewall before that.

**Hard gate with no exceptions:** the approved access control is **shared Caddy credentials plus a per-job `X-Job-Token`**, nothing else. If that decision is missing or gets replaced without fresh written Owner approval, stop the phase immediately. Never expose ports 3000, 8000, 8188, or 3389 publicly under any circumstance.

### Step 22: T085 — Owner approval gate (do this before anything else in this phase)

Send the Owner the following and **wait for written approval** before touching any public infrastructure:

| # | Decision needing approval |
|---|---|
| 1 | The model-license/territory scope of permitted users |
| 2 | Which domain or DDNS provider will be used |
| 3 | Who owns the credentials that will be issued |
| 4 | The current Public IP (revalidated fresh right now, not an old value) |
| 5 | Whether that IP is static, dynamic, or behind CGNAT |
| 6 | Whether the router can actually forward ports 80/443 |

Record the approval (or BLOCKED) in `evidence/public-deployment/owner-gate.md`.

**Expected result:** every item above is explicitly approved by the Owner in writing.

**If it fails:** if any item is not yet approved, record it as `BLOCKED` **without touching public infrastructure at all**. Never guess, and never proceed to Step 23.

### Step 23: T086 — Caddy configuration contract tests

Write `tests/security/test_caddy_contract.py` testing HTTPS-only access, Basic auth, request-body limit, `/api` proxying, stripping the Basic `Authorization` header, and banning public upstream binds.

```powershell
uv run --project apps/api pytest tests/security/test_caddy_contract.py
```

**Expected result:** the test fails because no Caddy config exists yet (test-first), and it includes assertions banning public 3000/8000/8188/3389.

**If it fails:** if the test doesn't cover everything T086 requires, fix the test first — never implement ahead of a controlling test.

### Step 24: T087 — Implement the Caddy configuration

Create `deploy/caddy/Caddyfile` and `deploy/caddy/.env.example` with hashed credential environment injection.

```powershell
caddy validate --config deploy/caddy/Caddyfile
```

**Expected result:** `caddy validate` passes, T086 passes, authenticated HTTPS routing works, the Basic header is actually stripped, and **no credential is committed**.

**If it fails:** never commit a Caddyfile with an embedded credential. Fix it to use environment variables only, then scan again before committing.

### Step 25: T088 — Windows Firewall boundary

Create `deploy/firewall/configure-public-boundary.ps1` (least-privilege) and `deploy/firewall/verify-public-boundary.ps1` (a read-only verifier).

**Expected result:** `evidence/public-deployment/firewall.md` records 443 allowed, 80 (if enabled) limited strictly to redirect/certificate use, and 3000/8000/8188/3389 **blocked**.

**If it fails:** if the verifier finds an internal port open, stop immediately — this security boundary must never be relaxed.

### Step 26: T089 — DNS/DDNS and router forwarding

Apply only the DNS/DDNS and port forwarding the Owner approved in T085. Forward only 80/443.

Record redacted before/after evidence (partially masking the IP as appropriate) in `evidence/public-deployment/dns-router.md`.

**Expected result:** public DNS resolves to the revalidated Public IP, no CGNAT/routing blocker remains, and **no internal port forward exists beyond 80/443**.

**If it fails:** if CGNAT appears or the router can't forward as reported in T085, stop and go back to the Owner immediately. Never look for another port to work around it.

### Step 27: T090 — TLS certificate and redirect validation

Run `scripts/verify/test_https_boundary.py`.

**Expected result:** `evidence/public-deployment/tls.md` shows trusted hostname validation, HTTPS 443 success, HTTP 80 doing only redirect/certificate issuance, and **no certificate warnings**.

**If it fails:** never use a self-signed certificate or bypass a warning to make it pass. Stop and fix the domain/DNS config instead.

### Step 28: T091 — Auth boundary tests from an external client

Run `scripts/verify/test_public_auth.py` from a machine outside the network.

**Expected result:** `evidence/public-deployment/auth.md` shows unauthenticated requests refused before any job is created, authenticated requests working, wrong-job tokens returning a uniform 404 (no hint whether the job exists), and **no credential or token leaking into any captured URL or log**.

**If it fails:** if a token leaks into a log or URL, stop immediately — that is sensitive data already exposed.

### Step 29: T092 — External port scan

Run `scripts/verify/test_external_ports.py` from outside the network.

**Expected result:** `evidence/public-deployment/ports.md` shows 443 (and 80 if enabled) behaving as expected, and **3000, 8000, 8188, and 3389 are all unreachable from outside**.

**If it fails:** if any internal port is reachable from outside, stop and close it before proceeding further.

**Phase 11 exit criteria:** the T085 owner gate is approved, TLS and two-layer access control both pass, only the intended public entry point is reachable, and no secret has been committed.

---

## Phase 12 — External-network acceptance and final audit (T093–T097)

> Enter this phase only after every Phase 11 exit criterion has passed.

### Step 30: T093 — External-network full-flow acceptance

Create and execute the checklist at `docs/operations/external-acceptance.md`.

**Expected result:** `evidence/public-deployment/full-flow.md` records a real authorized upload, real queue/process state, a complete textured-GLB preview (rotate/zoom/pan/reset), and a byte-identical download — all over real HTTPS from outside the network.

**If it fails:** record exactly where the flow broke and stop. LAN evidence is never a substitute for external evidence.

### Step 31: T094 — External-network security checklist

Create `docs/operations/external-network-security-checklist.md` and run `scripts/verify/test_external_acceptance.py` covering unauthorized, wrong-token, expired-job, invalid upload, low-disk admission, and internal-port cases.

**Expected result:** `evidence/public-deployment/negative-cases.md` shows a safe response for every case and **zero information leakage**.

**If it fails:** if any error message exposes internal detail (paths, stack traces, whether a job exists), stop and fix it first.

### Step 32: T095 — Operator runbook drill

Create `docs/operations/operator-runbook.md`, then actually rehearse it.

**Expected result:** `evidence/operations/runbook-drill.md` traces a Job ID across its full lifecycle — submission, queue, processing, result, download, failure, restart, 24-hour expiry, and low-disk recovery — without exposing user content or secrets.

**If it fails:** identify exactly which recovery step is incomplete and stop.

### Step 33: T096 — Final acceptance matrix

Create `evidence/final/mvp-acceptance.md`.

**Expected result:** every SC-001–SC-007 and FR-001–FR-018 in [spec.md](../../specs/001-local-3d-generation/spec.md) maps to real, passing evidence. Anything not yet passing must be marked `BLOCKED` honestly.

**If it fails:** never treat a checkbox or a report alone as proof — only a cited evidence file counts.

### Step 34: T097 — Final constitution and scope audit

Check against [constitution.md](../../.specify/memory/constitution.md) and record `evidence/final/constitution-audit.md`.

**Expected result:** no Post-MVP component (SDXL, Blender retopology, etc.) has crept in, every exception has a documented reason/risk/owner/review trigger, internal ports remain private, and the verdict is an honest `PASS` or `BLOCKED`.

**If it fails:** report `BLOCKED` with what still needs fixing. Never close it as PASS while something remains unresolved.

**Phase 12 exit criteria:** the external core flow, negative security checks, the operator recovery drill, the requirement-evidence matrix, and the constitution audit all pass — **this is the end of the MVP**.

## Verification

- [x] Git baseline: pushed to `R1KASAN/3D-Generate-by-AI-Local` after secret review — see [`evidence/setup/git-baseline.md`](../../evidence/setup/git-baseline.md).
- [ ] The machine in use is Windows with an NVIDIA GPU (not macOS).
- [ ] The Windows machine cloned the same baseline commit and `git status --short` is empty.
- [ ] `evidence/windows/gpu-baseline.md` contains real inventory.
- [ ] `evidence/windows/runtime-compatibility.md` contains real compatibility evidence.
- [ ] `evidence/windows/shape-smoke.md` contains a real API-driven shape artifact.
- [ ] `evidence/windows/object-info-check.md` contains real manifest/node validation.
- [ ] `docs/operations/windows-gpu-validation.md` contains the complete checklist.
- [ ] `evidence/windows/phase-7-gate.md` has an evidence-backed PASS/FAIL/BLOCKED verdict.
- [ ] `evidence/windows/comfy-adapter-smoke.md` contains real adapter results.
- [ ] `evidence/windows/textured-glb-validation.md` contains a real GLB passing every check.
- [ ] `evidence/windows/two-job-serial.md` proves isolation and concurrency = 1.
- [ ] `evidence/windows/recovery-matrix.md` shows zero duplicate executions.
- [ ] `evidence/windows/phase-9-gate.md` has an evidence-backed verdict.
- [ ] `evidence/lan/service-startup.md` and `evidence/lan/reboot-recovery.md` are complete.
- [ ] `evidence/lan/full-flow.md` shows the complete flow from a second device.
- [ ] `evidence/lan/isolation-and-ports.md` proves 8000/8188 are unreachable from the LAN.
- [ ] `evidence/lan/phase-10-gate.md` has an evidence-backed verdict.
- [ ] `evidence/public-deployment/owner-gate.md` has all six decisions approved by the Owner in writing.
- [ ] `evidence/public-deployment/firewall.md` confirms 3000/8000/8188/3389 are blocked from outside.
- [ ] `evidence/public-deployment/dns-router.md` confirms DNS points to a revalidated IP with no CGNAT blocker.
- [ ] `evidence/public-deployment/tls.md` confirms HTTPS passes with no certificate warnings.
- [ ] `evidence/public-deployment/auth.md` confirms no credential/token leaked into a log.
- [ ] `evidence/public-deployment/ports.md` confirms every internal port is unreachable from outside.
- [ ] `evidence/public-deployment/full-flow.md` contains a real external-user flow that passed over HTTPS.
- [ ] `evidence/public-deployment/negative-cases.md` confirms zero information leakage.
- [ ] `evidence/operations/runbook-drill.md` traces a Job ID across its full lifecycle.
- [ ] `evidence/final/mvp-acceptance.md` maps every SC/FR to real evidence.
- [ ] `evidence/final/constitution-audit.md` has an honest PASS or BLOCKED verdict.
- [ ] The three Phase 11 items have been reported to the Owner (domain/DDNS, IP type, router 80/443).

## Troubleshooting

| Symptom | Likely cause | Safe action |
|---|---|---|
| `nvidia-smi` does not work | Driver/GPU environment not ready | Stop at T058, capture output, have the Owner/administrator fix the driver first |
| `torch.cuda.is_available()` is `False` | PyTorch/CUDA/driver mismatch | Stop at T060, record versions, never upgrade at random |
| `/object_info` unreachable | ComfyUI not running or bound incorrectly | Check the process and local bind only; never open the firewall to fix it |
| Node class/hash does not match the manifest | Custom node/runtime drift | Stop at T062, pin and review the exact revision before retrying |
| Shape workflow passes in the GUI but fails via API | Incorrect API workflow export or mapping | Re-export the API format and keep API-only evidence |
| OOM or native wheel import failure | VRAM or runtime incompatibility | Stop and report BLOCKED; never lower an acceptance criterion yourself |
| Adapter tests pass on mock but fail on comfy | Contract drift between the two adapters | Fix the adapter to match the contract; never loosen the contract |
| More than one GLB is produced | Output resolver or Job ID prefix is wrong | Stop at T075; picking "the newest file" is never the fix |
| GLB has no texture or UVs | The shape workflow ran instead of shape+texture | Verify the correct workflow; never accept shape-only as a pass |
| Duplicate jobs after a restart | An auto-resubmit path exists | Stop at T078; reconcile via `/history` instead of resubmitting |
| Services do not start after reboot | Dependency order or service identity is wrong | Fix the service definition; starting it by hand is not a pass |
| A LAN device can reach 8000/8188 | Wrong bind or firewall rule | Stop at T083 immediately — this is a security boundary |
| `owner-gate.md` still has unapproved items | Not all questions asked, or the Owner hasn't answered yet | Stop at T085; never start T086 before every item is approved |
| Router can't forward 80/443 (ISP block or CGNAT) | The operator's network doesn't support port forwarding | Stop at T089; report to the Owner to consider an alternative (VPN) instead of forcing it open |
| A certificate warning or self-signed cert appears | DNS hasn't propagated yet, or the domain is wrong | Stop at T090; never bypass the warning, never deploy while a warning exists |
| A credential/token appears in a captured log | Logging isn't masking sensitive values | Stop at T091 immediately — treat this as a leak and rotate the credential |
| An internal port is reachable from outside during T092 | Firewall rules don't cover it fully | Stop immediately; take the service down until the firewall is fixed |

## Rollback

- Before changing a runtime, record versions/hashes and back up any configuration you modify.
- Uninstall or roll back only components the operator just installed and that have a documented rollback.
- Never delete models, evidence, the database, or project storage just to "try again".
- If Phase 10 services misbehave, stop the services and go back to manual runs to debug — never open extra ports to work around it.
- If Phase 11 has a problem after going public, **close the router's port forward first**, then debug — never leave it exposed while you investigate.
- After a rollback, re-run the T058 inventory and record what changed.

## Escalation

| Situation | Contact | Method |
|---|---|---|
| Someone proposes using macOS as the AI server | Project Owner | Refuse and cite the Hardware boundary in this document |
| GitHub repository/visibility/access is unclear | Project Owner | Report `BLOCKED` with the repository needing confirmation |
| GPU/driver/CUDA mismatch | Project Owner + Windows administrator | Attach sanitized inventory and the requested version decision |
| Manifest/node/license mismatch | Project Owner | Attach manifest evidence; never choose a revision alone |
| GLB repeatedly fails validation | Project Owner | Attach validation output; never lower the criteria yourself |
| A LAN client can reach an internal port | Project Owner | Report immediately as a security issue |
| A public-exposure request arrives before Phase 10 PASS | Project Owner | Refuse and cite the constitution/security boundary |
| The operator isn't comfortable opening their own router to the public | Project Owner | Say so before starting T085 so the Owner can consider an alternative (VPN) |
| Any T085 item cannot be answered | Project Owner | Record `BLOCKED` in `owner-gate.md` without touching public infrastructure |
| A credential/token leaks during T091 | Project Owner | Report immediately as a security incident and request credential rotation |
| A public-exposure request arrives before the owner gate passes | Project Owner | Refuse and cite Constitution principle IX plus T085 |

## History

| Date | Run By | Notes |
|---|---|---|
| 2026-09-03 | Not yet run | Runbook created from approved project artifacts; no Windows evidence claimed. |
| 2026-09-03 | Owner (macOS) | v1.1 — Git baseline created and pushed to `R1KASAN/3D-Generate-by-AI-Local` (public) after secret review; Step 0 changed from "create baseline" to "clone and verify baseline"; added Scope boundary and ComfyUI API integration rules |
| 2026-09-03 | Owner (macOS) | v2.0 — Renamed from `windows-phase7-operator-guide.*` to `windows-ai-server-runbook.*`; scope extended from Phase 7 only to Phase 7–10 (ending at a usable LAN deployment); added the Hardware boundary forbidding macOS as the AI server; added the Phase 11 preparation section requesting only domain/DDNS, IP type, and router 80/443 capability, without asking for the Public IP number; no Windows evidence claimed |
| 2026-09-03 | Owner (macOS) | v3.0 — Corrected a misunderstanding that Phase 10 required the Owner's own physical device (a second device belonging to the operator is sufficient); extended scope from Phase 7–10 to the full Phase 7–12 per the original spec, per the Owner's decision to proceed all the way to public deployment; added the Network boundary section explaining Phase 11 opens ports on the operator's own router and needs the operator's own consent, not just the Owner's instruction; added Steps 22–34 covering T085–T097 in full (owner-approval gate, Caddy, firewall, DNS/router, TLS, external auth test, port scan, external acceptance, negative-case security testing, operator runbook drill, final acceptance matrix, constitution audit); added public-deployment verification/troubleshooting/escalation entries; no Windows evidence claimed |
