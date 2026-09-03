# Checklist: Windows GPU Generation Validation (Phase 7 / T058–T062)

**Owner:** Windows Server Operator | **Frequency:** Once per server build, and again after any GPU, driver, CUDA, PyTorch, ComfyUI, or custom-node change | **Last Updated:** 2026-09-03 | **Last Run:** 2026-09-03 on `LAPTOP-9PI3K9F7`

> Filling in this checklist is not evidence. Each row is closed only by real
> command output or a real artifact path from the target Windows NVIDIA
> machine. A row with no output is `BLOCKED`, never `PASS`.

## Target machine of record

| Field | Value |
|---|---|
| Host | `LAPTOP-9PI3K9F7` |
| OS | Microsoft Windows 11 Home Single Language, 10.0.26200 build 26200, 64-bit |
| GPU | NVIDIA GeForce RTX 5070 Laptop GPU (Blackwell, `sm_120`) |
| VRAM | 8151 MiB total (~7.96 GiB usable by CUDA) |
| Driver | 592.15 (supports CUDA up to 13.1) |
| CUDA Toolkit | 12.8 (`nvcc` V12.8.61) |
| Python | 3.12.10 |
| PyTorch | 2.11.0+cu128 |
| Embedded SQLite | 3.49.1 |
| ComfyUI | v0.34.0, commit `345c9190497c82cff53e71fb4ae00d1e135a6542`, bound to `127.0.0.1:8188` |

## Section 1 — Prerequisites

| # | Item | Command | Result / artifact | Verdict |
|---|---|---|---|---|
| 1.1 | GPU present and driver healthy | `nvidia-smi` | `NVIDIA GeForce RTX 5070 Laptop GPU, 592.15, 8151 MiB` — full output in [gpu-baseline.md](../../evidence/windows/gpu-baseline.md) | **PASS** |
| 1.2 | Windows version captured | `Get-CimInstance Win32_OperatingSystem` | Windows 11 Home Single Language 10.0.26200 | **PASS** |
| 1.3 | Python 3.12 present | `py -3.12 --version` | `Python 3.12.10` | **PASS** |
| 1.4 | Embedded SQLite version captured | `py -3.12 -c "import sqlite3; print(sqlite3.sqlite_version)"` | `3.49.1` | **PASS** |
| 1.5 | CUDA Toolkit present | `nvcc --version` | `release 12.8, V12.8.61` | **PASS** |
| 1.6 | C++ build toolchain present (needed to compile native wheels) | `winget install Microsoft.VisualStudio.2022.BuildTools` (VCTools workload) | Installed 2026-09-03, exit code 0 | **PASS** |
| 1.7 | PyTorch sees the intended GPU | `python -c "import torch; torch.cuda.is_available()"` | `torch 2.11.0+cu128`, `cuda_available=True`, `device_name=NVIDIA GeForce RTX 5070 Laptop GPU`, `total_memory_bytes=8546484224` | **PASS** |
| 1.8 | Baseline captured to evidence | `scripts/windows/capture_gpu_baseline.ps1` | [evidence/windows/gpu-baseline.md](../../evidence/windows/gpu-baseline.md) | **PASS** (T058) |

## Section 2 — Runtime compatibility

| # | Item | Command | Result / artifact | Verdict |
|---|---|---|---|---|
| 2.1 | CUDA compute actually executes (not just reported available) | `verify_hunyuan_runtime.ps1` | `cuda_matmul_smoke=ok value=11.062681198120117` | **PASS** |
| 2.2 | All Hunyuan3D wrapper imports resolve | `verify_hunyuan_runtime.ps1` | 12/12 modules `import_ok`, `all_imports_ok=True` | **PASS** |
| 2.3 | No silent dependency upgrade | `verify_hunyuan_runtime.ps1` (pip freeze diff) | Baseline lock established at [hunyuan-runtime.lock.txt](../../evidence/windows/hunyuan-runtime.lock.txt) | **PASS** |
| 2.4 | Compatibility recorded to evidence | `scripts/windows/verify_hunyuan_runtime.ps1` | [evidence/windows/runtime-compatibility.md](../../evidence/windows/runtime-compatibility.md) | **PASS** (T060) |

> **Recorded deviation:** the plan originally pinned PyTorch 2.6 / CUDA 12.6.
> Those predate Blackwell and contain no `sm_120` kernels, so they cannot run
> on this GPU at all. Amended to PyTorch cu128 / CUDA 12.8 on 2026-09-03 —
> see `research.md` section 5 and `plan.md` Technical Context.

## Section 3 — Pinning and instance match

| # | Item | Command | Result / artifact | Verdict |
|---|---|---|---|---|
| 3.1 | ComfyUI + custom nodes pinned to exact commits | `git rev-parse HEAD` (×3) | ComfyUI `345c9190…`, Manager `b75fc664…`, Hunyuan3DWrapper `2609efa3…` | **PASS** |
| 3.2 | Wrapper commit matches the planning-time audited commit | compare with research.md §5 | `2609efa38f6a98292476f714839b7c1e5f9b699a` — identical | **PASS** |
| 3.3 | Instance bound to loopback only | `GET /system_stats` | `argv: ["main.py","--listen","127.0.0.1","--port","8188"]` | **PASS** |
| 3.4 | Post-restart health request succeeds | stop process → confirm refused → restart → `GET /system_stats` | pre-restart `exit 7` (refused), post-restart HTTP 200, same version, same commits | **PASS** |
| 3.5 | Pinning recorded to evidence | — | [evidence/windows/comfyui-pinning.md](../../evidence/windows/comfyui-pinning.md) | **PASS** (T059) |
| 3.6 | Manifest verifies against the live instance | `scripts/verify/verify_comfy_manifest.py` | `PASS: manifest … matches the running instance`, exit 0 | **PASS** |
| 3.7 | Deliberate mismatches fail closed | 4 corrupted fixtures + unreachable-port case | all exit 1 with specific errors — [object-info-check.md](../../evidence/windows/object-info-check.md) | **PASS** (T062) |

## Section 4 — Native shape smoke generation

| # | Item | Command | Result / artifact | Verdict |
|---|---|---|---|---|
| 4.1 | Pinned 2.1 shape checkpoint installed | download from `tencent/Hunyuan3D-2.1` | `hunyuan3d-dit-v2-1-model.fp16.ckpt`, 7,366,389,768 bytes | **PASS** |
| 4.2 | Model checkpoint content hash recorded | `certutil -hashfile … SHA256` | `6b519fc7242f78e9b5f47ea4d55668fe3d944a2d27332f4ca68d29a6ff603f5e`, pinned in the manifest | **PASS** |
| 4.3 | Workflow exported in both editable and API form | — | [editable](../../workflows/hunyuan3d/editable/hunyuan3d-21-shape-smoke.json), [api](../../workflows/hunyuan3d/api/hunyuan3d-21-shape-smoke.json) | **PASS** |
| 4.4 | Submission is API-only (no UI clicks) | `POST /prompt` | `prompt_id 1dedc9d8-3418-41d5-a7fe-73e972ff3932`, `node_errors: {}` | **PASS** |
| 4.5 | Job reaches success | `GET /history/{prompt_id}` | `status_str: success`, `completed: True`, 114.2 s | **PASS** |
| 4.6 | Exactly one non-empty GLB produced | filesystem enumeration | 1 file, 5,593,048 bytes, sha256 `8f3c9c3c…b15d8` | **PASS** |
| 4.7 | Artifact is a parseable mesh | `trimesh.load(...)` | `Scene`, `geometry_0` — 155,342 vertices / 310,680 faces | **PASS** |
| 4.8 | Shape smoke recorded to evidence | — | [evidence/windows/shape-smoke.md](../../evidence/windows/shape-smoke.md) | **PASS** (T061) |
| 4.9 | Result correctly **not** claimed as MVP completion | — | Marked shape-only throughout; no texture/UV/material requested or produced | **PASS** |

## Section 5 — Known constraints carried forward

| # | Finding | Impact | Status |
|---|---|---|---|
| 5.1 | The pinned wrapper's own nodes load the full fp16 model straight to GPU (~7.13 GiB) with no offload, which OOMs on this 8 GB card. Reproduced across a clean restart, with `--lowvram`, and with `rembg` moved to CPU. | Shape smoke could not run via upstream nodes as shipped | Worked around — see 5.2 |
| 5.2 | Project-owned `ComfyUI/custom_nodes/local3d_smoke_nodes.py` added, enabling the pinned pipeline's own (never-called) `enable_model_cpu_offload()`. Does **not** modify wrapper source. | Shape smoke passes on 8 GB | **PASS**, documented in manifest + shape-smoke.md |
| 5.3 | The MVP textured lane (T075) uses a **different** pipeline (Hunyuan3D 2.0 via `Hy3DModelLoader`), which was confirmed incompatible with the 2.1 checkpoint (`KeyError: 'model'`). Its VRAM behaviour is unproven and must not be assumed to fit. | Phase 9 risk | **OPEN** — verify at T075 |
| 5.4 | Texture generation additionally requires compiling `custom_rasterizer`; the wrapper ships prebuilt wheels only for torch 2.6/cu126, which do not match this torch 2.11/cu128 environment. | Phase 9 prerequisite | **OPEN** — build from source at T075 (VS Build Tools + CUDA 12.8 already installed, see 1.6) |

## Overall verdict

**PASS for T058–T062**. Every prerequisite and shape-smoke item closed with
real command output or an artifact path. The two Section 5 carry-forwards
(5.3 textured-lane VRAM behaviour, 5.4 `custom_rasterizer` build) remain
**OPEN against Phase 9**, not against this gate. No item in this checklist was
closed on configuration text alone.
