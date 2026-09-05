# Runbook: Windows NVIDIA AI Server — Hardware Gate to Public Deployment (Phase 7–12)

**Owner:** Windows Server Operator; opening public access always requires passing the feature-002 owner, permission, and management gates first | **Frequency:** As needed, once per server build | **Last Updated:** 2026-09-05 | **Last Run:** Not yet run

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
| 11 | Cloudflare-proxied HTTPS opens only after the feature-002 gates, with per-job token protection | T007–T026 |
| 12 | External-network testing plus the final project-closing audit | T035–T049 |

Stop immediately when any task is FAIL or BLOCKED. Never skip a gate merely to report progress. **Phase 11 carries a special condition**: it requires explicit, written owner approval, written network permission, and a proven origin management path before touching any public infrastructure (see feature-002 T007, T008, T021, and T055) — these are standing conditions of the phase, not ordinary checklist items.

## Hardware boundary (mandatory — read before anything else)

**The machine running the AI server must be Windows with an NVIDIA GPU. No exceptions.**

| Machine | Role | What it may and may not do |
|---|---|---|
| Windows + NVIDIA GPU | **The real AI server** | Runs ComfyUI, Hunyuan3D, FastAPI, GPU generation, and all LAN services — every piece of Phase 7–10 evidence must come from this machine |
| macOS (the Owner's MacBook) | **Development only** | Writing code, running the mock adapter, running non-GPU tests — **must never act as the AI server, and mock results must never substitute for Windows evidence** |

Reason: the MacBook has no NVIDIA GPU or CUDA, so it cannot run Hunyuan3D for real. Passing results from macOS belong to the mock lane (Phase 6, already closed) and are not evidence for this hardware gate.

If anyone proposes running the AI server on macOS, or using macOS results to close a Phase 7–10 task, refuse and report `BLOCKED`.

## Network boundary (important for Phase 11)

**Updated 2026-09-05:** this project does not use home/office router port
forwarding. The requested design retains a directly-assigned university public IP
(`161.200.90.4`, named in an Electrical Engineering Department memo dated
26 ธ.ค. 2567 — see `evidence/public-deployment/allocation-memo-review.md` for
what that document actually covers) for an **edge server**, which is a
separate machine from the Windows GPU server this runbook otherwise
describes. Live assignment and reachability remain deployment gates. The GPU server never holds a public IP; it connects outward to
the edge over a WireGuard tunnel. See
`C:\Users\MetaHosP\.claude\plans\router-ai-eventual-tide.md` and
`docs/operations/public-cutover.md` for the full architecture.

- There is no "operator's own router" decision to make — the gating
  authority is the **university border firewall**, not a consumer router.
  It must permit inbound `443/tcp` from Cloudflare's published ranges and
  `51820/udp` from any source to `161.200.90.4`; port 80 is not requested.
- The Windows GPU server stays on whatever network it is physically on
  (university, home, mobile hotspot) and is reachable only via the tunnel
  — it is explicitly designed to be able to move between networks freely.
  Do not attempt to forward ports on that machine's own router; nothing in
  this deployment depends on that.
- `161.200.90.3` is allocated to a different purpose and must never be
  configured, forwarded, or probed by anything related to this project.
- The domain used will point at the edge server's fixed address
  (`161.200.90.4`), not at the GPU server's own network IP, which changes
  as the GPU server moves.

## Source of truth

Read these before changing files or installing software:

- [Constitution](../../.specify/memory/constitution.md)
- [Specification](../../specs/001-local-3d-generation/spec.md)
- [Plan](../../specs/001-local-3d-generation/plan.md)
- [Tasks](../../specs/001-local-3d-generation/tasks.md)
- [Research decisions](../../specs/001-local-3d-generation/research.md)
- [Quickstart and gates](../../specs/001-local-3d-generation/quickstart.md)
- [Cloudflare public-entry specification](../../specs/002-cloudflare-public-entry/spec.md)
- [Cloudflare public-entry plan](../../specs/002-cloudflare-public-entry/plan.md)
- [Cloudflare public-entry tasks](../../specs/002-cloudflare-public-entry/tasks.md)
- [Cloudflare public-entry quickstart](../../specs/002-cloudflare-public-entry/quickstart.md)
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
| Changing access control away from "public entry + per-job token" | Requires a fresh Owner decision | The feature-002 owner gate records the current requested policy. Changing it needs written re-approval — never change it unilaterally. |
| Opening anything to the public before the feature-002 owner, permission, and management gates pass | Always stop | See the current Cloudflare public-entry section below. This condition has no exceptions. |

**About the Public IP:** it is not a secret, but avoid typing the raw number into chat/LINE — keep it in protected origin configuration and use the masked feature-002 evidence records instead.

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
- [ ] (For feature-002 public entry) written university IT permission for inbound 443/tcp from Cloudflare ranges and 51820/udp from any source to the approved origin is recorded; port 80 is not requested and there is no operator-router decision in this topology.

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

## Phase 11 — Cloudflare public entry and external acceptance (feature 002, superseded)

**Superseded by feature 003.** This entire section describes feature 002's
inbound-proxy architecture (Full-strict TLS, Authenticated Origin Pulls, an
Origin CA certificate, and a web service bound to the WireGuard tunnel
address) and is kept here only as historical record. The current source of
truth is `specs/003-outbound-tunnel-entry/tasks.md` and its `quickstart.md`,
which replace the inbound proxy with an **outbound** Cloudflare Tunnel
connector: the origin has no public listener at all, holds no certificate
secret, and the web service now starts independently of the WireGuard
binding (see `specs/003-outbound-tunnel-entry/contracts/compute-link.md`).
Do not follow the steps below on a feature-003 deployment; they describe a
design that has been actively removed, not merely superseded in name.

The former T085–T097 public-entry sequence is withdrawn and must not be
executed under feature 002 either.

### Current gates and sequence

1. Close the owner/model-license/territory gate and obtain written network
   permission for exactly `443/tcp` from current Cloudflare ranges and
   `51820/udp` from any source. Port 80 is not requested.
2. Decide and prove the origin management path from a fresh connection before
   any default-deny rule is applied.
3. Configure Cloudflare only after the gates are recorded: one proxied
   application hostname, Full (strict), Authenticated Origin Pulls, and an
   Origin CA certificate. Do not publish a DNS-only tunnel record.
4. Install and validate the origin Caddy configuration. It is 443-only,
   requires the provider client certificate, logs no project-controlled job
   credential, and proxies only to the laptop's WireGuard address.
5. Apply and verify the origin and laptop boundaries only on their target
   machines, then run all external, degraded-state, mobility, and recovery
   checks from the current feature's quickstart.

### Network boundary (current topology)

- Edge: `443/tcp` from Cloudflare ranges only; `51820/udp` from any source
  for authenticated WireGuard; management from its approved trusted source;
  everything else denied.
- GPU laptop: `10.10.0.2:3000` from `10.10.0.1/32` over WireGuard only;
  FastAPI and ComfyUI stay on loopback; RDP is denied.
- There is no operator-router port forwarding, no public port 80, and no
  LAN `portproxy` after cutover. Never recreate the stale LAN proxy.
- The laptop's physical address is not part of public configuration; moving
  networks must not require DNS, proxy, or tunnel-address edits.

### Required evidence

Use the feature-002 task IDs and record masked results under
`evidence/public-deployment/`. Do not treat LAN results as external proof.
The final release remains blocked until owner approval, management access,
provider controls, origin validation, positive WireGuard traversal, and the
off-campus full-flow/mobility evidence are all present.

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
- [ ] `deploy/cloudflare/dns-records.md` and the feature-002 external evidence confirm the proxied DNS record and no origin disclosure.
- [ ] `evidence/public-deployment/tls.md` confirms HTTPS passes with no certificate warnings.
- [ ] `evidence/public-deployment/auth.md` confirms no job token or other secret leaked into a log.
- [ ] `evidence/public-deployment/ports.md` confirms every internal port is unreachable from outside.
- [ ] `evidence/public-deployment/full-flow.md` contains a real external-user flow that passed over HTTPS.
- [ ] `evidence/public-deployment/negative-cases.md` confirms zero information leakage.
- [ ] `evidence/operations/runbook-drill.md` traces a Job ID across its full lifecycle.
- [ ] `evidence/final/mvp-acceptance.md` maps every SC/FR to real evidence.
- [ ] `evidence/final/constitution-audit.md` has an honest PASS or BLOCKED verdict.
- [ ] The feature-002 gate items have been reported to the Owner (domain/account, model-license/territory, management path, and written 443/51820 permission).

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
| `owner-gate.md` still has unapproved items | Not all questions asked, or the Owner hasn't answered yet | Stop at the feature-002 gates; never start live setup before T007, T008, T021, and T055 are closed |
| University border firewall won't permit the required 443/51820 flows to the approved origin | IT policy hasn't approved it yet, or the request targeted the wrong address | Stop at feature-002 T007; report to the Owner. Never substitute the alternate address or another port to work around it. |
| WireGuard tunnel won't come up between edge and laptop | Border firewall doesn't actually have 51820/udp open, `PersistentKeepalive` missing, or a competing VPN adapter took the default route | See `docs/operations/tunnel-setup.md` Troubleshooting; this is diagnosed at the tunnel layer, never fixed by restarting the web service |
| A certificate warning or self-signed cert appears | DNS hasn't propagated yet, or the domain is wrong | Stop at feature-002 T025; never bypass the warning, never deploy while a warning exists |
| A job token or other secret appears in a captured log | Logging isn't masking sensitive values | Stop at feature-002 T014/T026 immediately — treat this as a leak and invalidate the affected token or rotate the affected secret |
| An internal port is reachable from outside during feature-002 validation | Firewall rules don't cover it fully | Stop immediately; take the service down until the firewall is fixed |
| **(feature 003)** Visitor sees Cloudflare's own error page (e.g. a 1033/502/530-style provider page) instead of the application | The approved origin is powered off, or its `cloudflared` connector cannot reach the edge — this is **expected, documented behavior** (FR-025a), not an application fault | Check origin power/network and the connector's own status (`curl -sf http://127.0.0.1:20241/ready` on the origin, per `deploy/cloudflared/README.md`) **before** touching the GPU laptop or any application service. A provider error page with the origin actually healthy means DNS or the tunnel route is misconfigured, not that the app crashed. |
| **(feature 003)** `/api/v1/health/ready` is `200` but the site shows a generation failure with `engine_unavailable` | `/ready` only reflects startup configuration and never changes afterward; it does not detect a live engine hang | Check `/api/v1/health/engine` instead — it performs a real, short-timeout probe. See `specs/003-outbound-tunnel-entry/spec.md` FR-025 and `apps/api/src/local3d/api/health.py`. |
| **(feature 003)** GPU laptop won't serve the LAN after a reboot while WireGuard is down | A stale assumption that the web service needs the tunnel to start | This must not happen under feature 003 — `scripts/windows/start_web_service.ps1` starts unconditionally on loopback. If it does happen, `deploy/windows/services/web.xml` may have regressed to a feature-002-style tunnel-address bind; check it against `specs/003-outbound-tunnel-entry/contracts/compute-link.md` C4. |

## Rollback

- Before changing a runtime, record versions/hashes and back up any configuration you modify.
- Uninstall or roll back only components the operator just installed and that have a documented rollback.
- Never delete models, evidence, the database, or project storage just to "try again".
- If Phase 10 services misbehave, stop the services and go back to manual runs to debug — never open extra ports to work around it.
- If Phase 11 has a problem after going public, **disable the edge's public firewall rules first** (`deploy/firewall/configure-public-edge.ps1` was applied — remove or disable the rules it created), then debug — never leave it exposed while you investigate.
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
| The edge server's management access (SSH/console) isn't confirmed working yet | Project Owner / university IT | Say so before running `configure-public-edge.ps1` — that script pre-flight-checks this, but the decision of which management path to use (Stage 0.1 of the deployment plan) must be made first |
| Any feature-002 gate item cannot be answered | Project Owner | Record `BLOCKED` in `owner-gate.md` without touching public infrastructure |
| A job token or other secret leaks during feature-002 validation | Project Owner | Report immediately as a security incident and invalidate the affected token or rotate the affected secret |
| A public-exposure request arrives before the feature-002 owner gate passes | Project Owner | Refuse and cite Constitution principle IX plus the feature-002 task ledger |

## History

| Date | Run By | Notes |
|---|---|---|
| 2026-09-03 | Not yet run | Runbook created from approved project artifacts; no Windows evidence claimed. |
| 2026-09-03 | Owner (macOS) | v1.1 — Git baseline created and pushed to `R1KASAN/3D-Generate-by-AI-Local` (public) after secret review; Step 0 changed from "create baseline" to "clone and verify baseline"; added Scope boundary and ComfyUI API integration rules |
| 2026-09-03 | Owner (macOS) | v2.0 — Renamed from `windows-phase7-operator-guide.*` to `windows-ai-server-runbook.*`; scope extended from Phase 7 only to Phase 7–10 (ending at a usable LAN deployment); added the Hardware boundary forbidding macOS as the AI server; added the Phase 11 preparation section requesting only domain/DDNS, IP type, and router 80/443 capability, without asking for the Public IP number; no Windows evidence claimed |
| 2026-09-03 | Owner (macOS) | v3.0 — Corrected a misunderstanding that Phase 10 required the Owner's own physical device (a second device belonging to the operator is sufficient); extended scope from Phase 7–10 to the full Phase 7–12 per the original spec, per the Owner's decision to proceed all the way to public deployment; added the Network boundary section explaining Phase 11 opens ports on the operator's own router and needs the operator's own consent, not just the Owner's instruction; added Steps 22–34 covering T085–T097 in full (owner-approval gate, Caddy, firewall, DNS/router, TLS, external auth test, port scan, external acceptance, negative-case security testing, operator runbook drill, final acceptance matrix, constitution audit); added public-deployment verification/troubleshooting/escalation entries; no Windows evidence claimed |
| 2026-09-04 | Claude (public-deployment planning) | v4.0 — Replaced the operator-own-router model with the actual approved topology: a university-assigned public IP (`161.200.90.4`) on a separate edge server, reached over a WireGuard tunnel from the GPU laptop, so the laptop can move between networks. Rewrote the Network boundary section, Step 22's owner-gate items, Step 26 (T089, now a border-firewall confirmation rather than router forwarding), and the related checklist/troubleshooting/escalation entries. Constitution amended to 1.1.0 in the same change to permit the approved no-site-wide-login policy explicitly. See `C:\Users\MetaHosP\.claude\plans\router-ai-eventual-tide.md` for full rationale; no Windows evidence claimed. |
