# Runbook: Windows NVIDIA Compatibility Gate (Phase 7)

**Owner:** Windows Server Operator; GitHub publication requires Owner approval | **Frequency:** As needed, once per target server build | **Last Updated:** 2026-09-03 | **Last Run:** Not yet run

**Document version:** 1.1 | **Source language:** Thai | **Thai source:** [windows-phase7-operator-guide.th.md](windows-phase7-operator-guide.th.md), version 1.1

> This is a Phase 7 operational guide only. Writing or reading it is not evidence that Windows, an NVIDIA GPU, ComfyUI, Hunyuan3D, or a GLB result has passed.

## Purpose

Verify that the target Windows PC has a pinned runtime capable of a native Hunyuan3D 2.1 shape smoke test before real ComfyUI-adapter or textured-GLB work begins. Execute `T058 → T059 → T060 → T061 → T062 → T063 → T064` in order. Stop immediately when any task is FAIL or BLOCKED.

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

Phase 7 proves **runtime compatibility only**. It is not model quality and it is not deployment.

**In scope for Phase 7:** T058–T064 — inventory, pinned install, compatibility checks, native shape smoke, manifest verification, checklist, and gate verdict.

**Out of scope — do not do these in this phase:**

| Topic | Status | Reason |
|---|---|---|
| SDXL re-texturing / ControlNet texture projection | Post-MVP quality lane | Reference only. Never add to the MVP workflow, dependencies, or task completion criteria. |
| Blender retopology, Quad Remesher, texture painting, texture baking | Post-MVP quality lane | Manual post-MVP work, not part of the FastAPI/ComfyUI pipeline. |
| Textured-GLB acceptance, FastAPI-to-ComfyUI integration | Phase 8 and later | A passing shape smoke does not count as MVP acceptance. |
| LAN, Caddy, firewall, DNS, HTTPS, public deployment | Phase 9 and later | Requires a Phase 7 gate PASS first. |

**Values that must not become requirements:** tuning numbers found in external videos or tutorials — such as `steps=100`, octree resolution `900–1000`, or a face count of `1,000,000` — are **experimental values**, not MVP requirements. Prove them against the real machine's VRAM and record the values actually used in the manifest.

**CUDA 12.6** is a planning candidate consistent with the wrapper, but never install it blindly from a video. It must pass T058–T060 and be pinned in the manifest first.

**Status of external videos and tutorials:** *reference only*, per the [source register](../reference/ai-runtime-sources.md). They never substitute for real Windows evidence and never close a task.

## ComfyUI API integration rules

These rules apply from Phase 7 onward and remain binding in Phase 8.

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

- [x] The Owner has confirmed the GitHub destination: [`R1KASAN/3D-Generate-by-AI-Local`](https://github.com/R1KASAN/3D-Generate-by-AI-Local), visibility `public` — baseline commit `fefad6e` is pushed (see Step 0).
- [ ] The operator has local-administrator access only when a pinned installer requires it.
- [ ] The operator can write to the project root, evidence directory, and local runtime directory.
- [ ] The PC has an NVIDIA GPU ready for testing and sufficient free disk for manifest-defined runtime/model assets.
- [ ] ComfyUI, FastAPI, and browser services are not Internet-facing; ports `3000`, `8000`, `8188`, and `3389` remain private.
- [ ] The operator has read every Source-of-truth artifact.

## Procedure

### Step 0: Clone and verify the Git baseline on the Windows machine

> **Status: the baseline is already created and pushed.** The operator does not create a new commit or repository. This step is to *fetch and verify* that the Windows machine has exactly the source the Owner reviewed.

Confirmed baseline:

| Item | Value |
|---|---|
| Repository | [`R1KASAN/3D-Generate-by-AI-Local`](https://github.com/R1KASAN/3D-Generate-by-AI-Local) |
| Visibility | `public` (Owner confirmed) |
| Default branch | `main` |
| Baseline commit | `fefad6ec10d2e96405b34efb0d0e4352258ab3b4` |
| Scope | 150 source/spec/docs files — passed secret review; no model weights, runtime artifacts, or credentials |

Clone on the Windows machine:

```powershell
Set-Location <PARENT_DIRECTORY>
git clone https://github.com/R1KASAN/3D-Generate-by-AI-Local.git
Set-Location 3D-Generate-by-AI-Local
git log -1 --format=%H
git status --short
```

**Expected result:** `git log -1 --format=%H` returns `fefad6ec10d2e96405b34efb0d0e4352258ab3b4` (or a newer commit the Owner has announced), and `git status --short` is empty.

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

### Step 1: T058 — Hardware/runtime inventory

Create and execute `scripts/windows/capture_gpu_baseline.ps1` as T058 requires, then save sanitized output in `evidence/windows/gpu-baseline.md`.

Minimum commands to record:

```powershell
nvidia-smi
py -3.12 -c "import platform; print(platform.platform())"
py -3.12 -c "import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0)); print(torch.cuda.get_device_properties(0).total_memory)"
py -3.12 -c "import sqlite3; print(sqlite3.sqlite_version)"
Get-PSDrive -PSProvider FileSystem
```

**Expected result:** observed Windows version, GPU model, driver, VRAM, Python, PyTorch, CUDA availability, SQLite version, and disk capacity.

**If it fails:** do not make random installation/version changes. Record the missing or mismatched component and stop as `BLOCKED`.

### Step 2: T059 — Pinned ComfyUI/custom nodes

Use the [runtime source register](../reference/ai-runtime-sources.md) for installation guidance, but select revisions, packages, models, and nodes only from the reviewed workflow manifest.

- Bind ComfyUI to loopback, for example `127.0.0.1:8188`.
- Record ComfyUI, wrapper, custom-node, model, and license commit/hash/version data.
- Do not allow ComfyUI Manager unattended updates.
- Restart, then check health from localhost only.

```powershell
Invoke-WebRequest http://127.0.0.1:8188/object_info -UseBasicParsing
```

**Expected result:** ComfyUI responds on loopback and versions/hashes match the manifest.

**If it fails:** stop before T060. Record the exact sanitized mismatch and resolve it through a manifest/runtime owner decision.

### Step 3: T060 — PyTorch/CUDA/native-wheel compatibility

Create and run `scripts/windows/verify_hunyuan_runtime.ps1` as T060 requires. Do not auto-upgrade dependencies to force an import.

```powershell
py -3.12 -c "import torch; assert torch.cuda.is_available(); print(torch.version.cuda); print(torch.cuda.get_device_name(0))"
```

**Expected result:** the real environment imports required packages, CUDA is available, the intended GPU is selected, and no manifest drift exists.

**If it fails:** record installed versions and sanitized errors in `evidence/windows/runtime-compatibility.md`; stop as `BLOCKED` until the Owner approves a dependency decision.

### Step 4: T061 — Native Hunyuan3D 2.1 shape smoke

Export editable and API workflows to the paths required by T061, execute the API workflow, and retain a parseable shape artifact.

**Expected result:** API-driven shape smoke evidence in `evidence/windows/shape-smoke.md`.

**If it fails:** retain workflow hash, node/version mismatch, and safe error. GUI-only success is not API evidence.

> A shape-only artifact is not a textured GLB and does not satisfy MVP acceptance.

### Step 5: T062 — Manifest/hash and `/object_info`

Create and execute `scripts/verify/verify_comfy_manifest.py` as T062 requires, including the deliberate mismatch fixture.

**Expected result:** the pinned runtime passes; missing/changed nodes or mismatched hashes fail closed.

**If it fails:** stop before T063 and record the mismatch in `evidence/windows/object-info-check.md`. Do not guess a compatible version.

### Step 6: T063 — Windows GPU validation checklist

Create [windows-gpu-validation.md](windows-gpu-validation.md) as T063 requires. Complete every prerequisite with command output, artifact paths, and a `PASS`, `FAIL`, or `BLOCKED` verdict.

**Expected result:** no skipped item and every claim references current evidence.

**If it fails:** state the smallest blocker and requested Owner action.

### Step 7: T064 — Phase 7 gate verdict

Create `evidence/windows/phase-7-gate.md` using:

```text
Gate: Phase 7 — Windows ComfyUI and Hunyuan3D Compatibility
Date/time and operator:
Host/environment:
Pinned revisions/hashes:
Tasks T058–T063 and evidence links:
Verdict: PASS | FAIL | BLOCKED
Blocker and smallest owner action:
```

**Expected result:** PASS only when T058–T063 all pass. Otherwise, honestly record FAIL or BLOCKED.

**If it fails:** do not continue to T068, T072, T075, LAN, or public deployment.

## Verification

- [x] Git baseline: commit `fefad6e` pushed to `R1KASAN/3D-Generate-by-AI-Local` after secret review — see [`evidence/setup/git-baseline.md`](../../evidence/setup/git-baseline.md).
- [ ] The Windows machine cloned the same baseline commit and `git status --short` is empty.
- [ ] `evidence/windows/gpu-baseline.md` contains real inventory.
- [ ] `evidence/windows/runtime-compatibility.md` contains real compatibility evidence.
- [ ] `evidence/windows/shape-smoke.md` contains a real API-driven shape artifact.
- [ ] `evidence/windows/object-info-check.md` contains real manifest/node validation.
- [ ] `docs/operations/windows-gpu-validation.md` contains the complete checklist.
- [ ] `evidence/windows/phase-7-gate.md` has an evidence-backed PASS/FAIL/BLOCKED verdict.

## Troubleshooting

| Symptom | Likely cause | Safe action |
|---|---|---|
| `nvidia-smi` fails | Driver or GPU environment is unavailable | Stop T058, retain output, and ask the Owner/administrator to repair the driver. |
| `torch.cuda.is_available()` is `False` | PyTorch/CUDA/driver mismatch | Stop T060, record versions, and do not perform random upgrades. |
| `/object_info` is unreachable | ComfyUI is not running or has the wrong bind | Check process/loopback binding only; never open a firewall as a workaround. |
| Node class/hash differs from manifest | Custom-node/runtime drift | Stop T062 and pin/review the exact revision before retrying. |
| GUI passes but API fails | API workflow export or mapping is wrong | Export API format again and retain API evidence only. |
| OOM or native-wheel import fails | Insufficient VRAM or runtime incompatibility | Stop and report BLOCKED; never weaken acceptance criteria. |

## Rollback

- Record version/hash data and back up changed configuration before changing runtime components.
- Roll back only the component installed in the current procedure and only with a documented rollback.
- Never delete models, evidence, databases, or project storage merely to retry.
- After a rollback, repeat T058 inventory and record the change.

## Escalation

| Situation | Contact | Method |
|---|---|---|
| GitHub repository, visibility, or access is unknown | Project Owner | Report BLOCKED with the exact decision needed. |
| GPU/driver/CUDA mismatch | Project Owner + Windows administrator | Attach sanitized inventory and requested version decision. |
| Manifest/node/license mismatch | Project Owner | Attach manifest evidence; do not choose revisions yourself. |
| Public exposure requested before Phase 7 PASS | Project Owner | Refuse and cite the constitution/security boundary. |

## History

| Date | Run By | Notes |
|---|---|---|
| 2026-09-03 | Not yet run | Runbook created from approved project artifacts; no Windows evidence claimed. |
| 2026-09-03 | Owner (macOS) | v1.1 — Git baseline `fefad6e` created and pushed to `R1KASAN/3D-Generate-by-AI-Local` (public) after secret review; Step 0 changed from "create baseline" to "clone and verify baseline"; added Scope boundary and ComfyUI API integration rules; no Windows evidence claimed. |
