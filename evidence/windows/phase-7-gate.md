# Phase 7 Compatibility Gate Verdict (T064)

**Gate**: Phase 7 — Windows ComfyUI and Hunyuan3D compatibility validation
**Date/time and operator**: 2026-09-03, MetaHosP
**Host/environment**: `LAPTOP-9PI3K9F7` — Windows 11 Home Single Language 10.0.26200, NVIDIA GeForce RTX 5070 Laptop GPU (8151 MiB), driver 592.15
**Scope of this verdict**: the pinned runtime and required nodes are compatible
on the real server, and a native shape smoke test executes. This verdict makes
**no** textured-GLB, LAN, reboot, or public-network claim.

## Task results

| Task | Requirement | Evidence | Verdict |
|---|---|---|---|
| T058 | Hardware/runtime inventory captured and reviewed | [gpu-baseline.md](gpu-baseline.md) | **PASS** |
| T059 | ComfyUI + custom nodes pinned; commits match the running `127.0.0.1:8188` instance; post-restart health succeeds | [comfyui-pinning.md](comfyui-pinning.md), [workflow-manifest.json](../../workflows/hunyuan3d/workflow-manifest.json) | **PASS** |
| T060 | CUDA available, intended GPU selected, imports succeed, no silent dependency upgrade | [runtime-compatibility.md](runtime-compatibility.md), [hunyuan-runtime.lock.txt](hunyuan-runtime.lock.txt) | **PASS** |
| T061 | API-submitted native 2.1 shape workflow produces a parseable shape artifact, marked not-MVP | [shape-smoke.md](shape-smoke.md), [artifact](artifacts/hunyuan3d-21-shape-smoke.glb) | **PASS** |
| T062 | Manifest/hash/`/object_info` verification passes on the pinned instance and fails closed on deliberate mismatches | [object-info-check.md](object-info-check.md), [verify_comfy_manifest.py](../../scripts/verify/verify_comfy_manifest.py) | **PASS** |
| T063 | Windows GPU generation checklist executed with output/artifact paths and explicit verdicts | [windows-gpu-validation.md](../../docs/operations/windows-gpu-validation.md) | **PASS** |

## Pinned revision and hash set of record

| Component | Pin |
|---|---|
| ComfyUI | `345c9190497c82cff53e71fb4ae00d1e135a6542` (v0.34.0) |
| ComfyUI-Manager | `b75fc664ecab9c4602380d9660833d02f6a63333` |
| ComfyUI-Hunyuan3DWrapper | `2609efa38f6a98292476f714839b7c1e5f9b699a` |
| `local3d_smoke_nodes.py` | project-owned, not upstream — T061 scope only |
| Hunyuan3D 2.1 shape checkpoint | `6b519fc7242f78e9b5f47ea4d55668fe3d944a2d27332f4ca68d29a6ff603f5e` (7,366,389,768 bytes) |
| Shape smoke API workflow | `02a21366f523885ee7c1603fa9bd7204964ce22e87999b50d737e2be1a63bd56` |
| Shape smoke editable workflow | `7f28104984c8b81ae3e9eabb4013c4d028087655aed63807be962d4b3a79a7df` |
| Shape smoke result GLB | `8f3c9c3ce26a6f019131907cc555b5d18bfa2971df56a790d6c7cb9ecb8b15d8` |
| Runtime | Python 3.12.10, PyTorch 2.11.0+cu128, CUDA Toolkit 12.8, SQLite 3.49.1 |

## Amendments made during this phase

1. **Pinned runtime versions amended.** `plan.md` and `research.md` §5
   originally pinned PyTorch 2.6 / CUDA 12.6. The provisioned GPU is Blackwell
   (`sm_120`); those versions contain no kernels for it and cannot execute on
   this hardware regardless of driver. Amended to PyTorch cu128 / CUDA 12.8 and
   verified by real execution (`torch.cuda.is_available() → True`, GPU matmul
   smoke). `docs/reference/ai-runtime-sources.md` updated to the 12.8 archive.
2. **Project-owned custom node added.** `ComfyUI/custom_nodes/local3d_smoke_nodes.py`
   enables the pinned wrapper pipeline's own (never-called)
   `enable_model_cpu_offload()` so the 2.1 model fits this 8 GB GPU. It does not
   modify any file in the pinned wrapper commit, which still verifies clean.
   Reason, risk, and review trigger are recorded in [shape-smoke.md](shape-smoke.md).

## Open items carried into later phases

These do **not** block Phase 7. They are recorded so they are not rediscovered
as surprises:

| # | Item | Blocks |
|---|---|---|
| 1 | The MVP textured lane uses the separate Hunyuan3D **2.0** pipeline (`Hy3DModelLoader`), confirmed incompatible with the 2.1 checkpoint (`KeyError: 'model'`). Its model, VRAM behaviour, and licence review are all unproven. | T075 |
| 2 | This 8 GB GPU could not run even shape-only generation through the wrapper's stock un-offloaded loading path. Texture generation is heavier; it must not be assumed to fit. | T075, T077 (two serial jobs without OOM) |
| 3 | `custom_rasterizer` must be compiled from source for texture generation — the wrapper's prebuilt wheels target torch 2.6/cu126, not this torch 2.11/cu128 environment. Prerequisites (VS Build Tools, CUDA 12.8 `nvcc`) are installed. | T075 |
| 4 | Model licence/territory review for the pinned artifacts has not been performed. | T085 owner gate |

## Verdict

**PASS.**

T058–T063 are all PASS on the real Windows NVIDIA server. The pinned runtime
and required node set are compatible with this machine, and a native
Hunyuan3D 2.1 shape smoke test generated one parseable GLB through API-only
submission.

Per `tasks.md`, a shape smoke PASS unlocks adapter work (Phase 8) but **does
not satisfy the MVP**. The textured-GLB requirement remains entirely unproven
and is explicitly not claimed by this verdict.
