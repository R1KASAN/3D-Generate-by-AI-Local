# Runbook: Windows NVIDIA AI Server — Hardware Gate to LAN Delivery (Phase 7–10)

**Owner:** Windows Server Operator; opening public access requires Owner approval | **Frequency:** As needed, once per server build | **Last Updated:** 2026-09-03 | **Last Run:** Not yet run

**Document version:** 2.0 | **Source language:** Thai | **Thai source:** [windows-ai-server-runbook.th.md](windows-ai-server-runbook.th.md), version 2.0

> This is a repeatable operational guide for Phase 7 through Phase 10. Writing or reading it is not evidence that Windows, an NVIDIA GPU, ComfyUI, Hunyuan3D, a GLB, or the LAN flow has passed. Evidence must come from real runs on the target machine.

## Purpose

Take the Windows NVIDIA server from "bare machine" to "AI server genuinely usable over the LAN", passing each gate in order:

| Phase | What must be proven | Tasks |
|---|---|---|
| 7 | The pinned runtime can execute a native shape smoke test | T058–T064 |
| 8 | FastAPI talks to real ComfyUI through the same adapter contract as the mock | T068, T072–T074 |
| 9 | A **real textured GLB** is produced and jobs stay isolated | T075–T079 |
| 10 | The full web flow works from a **second device on the LAN** | T080–T084 |

Stop immediately when any task is FAIL or BLOCKED. Never skip a gate merely to report progress.

## Hardware boundary (mandatory — read before anything else)

**The machine running the AI server must be Windows with an NVIDIA GPU. No exceptions.**

| Machine | Role | What it may and may not do |
|---|---|---|
| Windows + NVIDIA GPU | **The real AI server** | Runs ComfyUI, Hunyuan3D, FastAPI, GPU generation, and all LAN services — every piece of Phase 7–10 evidence must come from this machine |
| macOS (the Owner's MacBook) | **Development only** | Writing code, running the mock adapter, running non-GPU tests — **must never act as the AI server, and mock results must never substitute for Windows evidence** |

Reason: the MacBook has no NVIDIA GPU or CUDA, so it cannot run Hunyuan3D for real. Passing results from macOS belong to the mock lane (Phase 6, already closed) and are not evidence for this hardware gate.

If anyone proposes running the AI server on macOS, or using macOS results to close a Phase 7–10 task, refuse and report `BLOCKED`.

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

**In scope for this runbook:** Phase 7 → 8 → 9 → 10 in order, ending at a working LAN deployment.

**Out of scope — do not do these:**

| Topic | Status | Reason |
|---|---|---|
| SDXL re-texturing / ControlNet texture projection | Post-MVP quality lane | Reference only. Never add to the MVP workflow, dependencies, or task completion criteria. |
| Blender retopology, Quad Remesher, texture painting, texture baking | Post-MVP quality lane | Manual post-MVP work, not part of the FastAPI/ComfyUI pipeline. |
| Caddy, DNS, DDNS, HTTPS certificates, router port-forwarding, public firewall | **Phase 11 — hard gate** | Requires fresh Owner approval per T085 before any work starts. See "Preparing for Phase 11". |
| Sending the Public IP to the Owner right now | Not needed yet | See "Preparing for Phase 11" — only three items are needed now, and the IP number is not one of them. |

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
- [ ] ComfyUI, FastAPI, and browser services are not Internet-facing; ports `3000`, `8000`, `8188`, and `3389` remain private.
- [ ] The operator has read every Source-of-truth artifact.

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

## Preparing for Phase 11 (Public Deployment) — stop and report

> **Stop here.** Phase 11 is a hard gate under T085 and [Constitution principle IX](../../.specify/memory/constitution.md) — public access control and deployment exposure require Owner approval. The operator must never decide these alone.

**Do not touch before you get the green light:** domain, DNS, DDNS, Caddy config, HTTPS certificates, router port-forwarding, public firewall rules.

**What to report to the Owner once Phase 10 = PASS** (these three items only):

| # | Information needed | Why it matters |
|---|---|---|
| 1 | Whether a domain already exists, or which DDNS provider will be used | Caddy issues the HTTPS certificate from a domain name, not from an IP number |
| 2 | Whether the Public IP is **static**, **dynamic**, or behind **CGNAT** | Behind CGNAT, port forwarding is impossible and the whole deployment approach must change |
| 3 | Whether the router can forward ports `80/443` | If it cannot, Phase 11 must be redesigned before it starts |

**Do not send the Public IP number yet.** A Public IP is not a secret, but it is not needed until DNS is actually being configured and tested from the Internet. At that point the Owner will ask you to revalidate the current value, because anything sent in advance may already be stale.

**Expected result:** the Owner receives the three items above plus a link to `evidence/lan/phase-10-gate.md`, and replies with either approval or BLOCKED.

**If it fails:** if any of the three cannot be answered, report that it cannot be answered. Never guess, and never start Phase 11.

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

## Rollback

- Before changing a runtime, record versions/hashes and back up any configuration you modify.
- Uninstall or roll back only components the operator just installed and that have a documented rollback.
- Never delete models, evidence, the database, or project storage just to "try again".
- If Phase 10 services misbehave, stop the services and go back to manual runs to debug — never open extra ports to work around it.
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
| Ready for Phase 11 | Project Owner | Send the three items (domain/DDNS, IP type, router 80/443) plus a link to `evidence/lan/phase-10-gate.md` |

## History

| Date | Run By | Notes |
|---|---|---|
| 2026-09-03 | Not yet run | Runbook created from approved project artifacts; no Windows evidence claimed. |
| 2026-09-03 | Owner (macOS) | v1.1 — Git baseline created and pushed to `R1KASAN/3D-Generate-by-AI-Local` (public) after secret review; Step 0 changed from "create baseline" to "clone and verify baseline"; added Scope boundary and ComfyUI API integration rules |
| 2026-09-03 | Owner (macOS) | v2.0 — Renamed from `windows-phase7-operator-guide.*` to `windows-ai-server-runbook.*`; scope extended from Phase 7 only to Phase 7–10 (ending at a usable LAN deployment); added the Hardware boundary forbidding macOS as the AI server; added the Phase 11 preparation section requesting only domain/DDNS, IP type, and router 80/443 capability, without asking for the Public IP number; no Windows evidence claimed |
