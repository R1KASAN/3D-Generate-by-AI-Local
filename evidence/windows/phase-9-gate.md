# Phase 9 Real GPU Textured-GLB Gate (T079)

**Date/time:** 2026-09-03 (UTC)

**Host:** `LAPTOP-9PI3K9F7`, Windows 11 Home Single Language 10.0.26200,
NVIDIA GeForce RTX 5070 Laptop GPU (Blackwell, 8151 MiB), driver 592.15.

## Task verdicts

| Task | Evidence | Verdict |
|---|---|---|
| T075 | [textured-generation-1.md](textured-generation-1.md) | **PASS** |
| T076 | [textured-glb-validation.md](textured-glb-validation.md) | **PASS** |
| T077 | [two-job-serial.md](two-job-serial.md) | **PASS** |
| T078 | [recovery-matrix.md](recovery-matrix.md) | **PASS** |

## Pinned revision/hash set

| Component | Pin |
|---|---|
| ComfyUI | commit `345c9190497c82cff53e71fb4ae00d1e135a6542`, v0.34.0 |
| ComfyUI-Manager | commit `b75fc664ecab9c4602380d9660833d02f6a63333` |
| ComfyUI-Hunyuan3DWrapper | commit `2609efa38f6a98292476f714839b7c1e5f9b699a` |
| API workflow | `f0ab76f6bfc65eb9bd130fe8d7dd2eadb80ec263a96aca76b7a24d78bb30d36a` |
| Editable workflow | `b990fab37fbd800fdbbb9a9f2eba9e7eede3a4296d43be0015c13f21163e5f42` |
| Hunyuan3D 2.0 shape model | 4,928,151,594 bytes; `ccda5cb4327111112a0aacd2b6798a7a6735e0ceece3b402b44999dada79595e` |
| Delight model snapshot | 13 files; 4,313,519,161 bytes; [file hashes](textured-model-hashes.md) |
| Paint model snapshot | 16 files; 5,527,960,505 bytes; [file hashes](textured-model-hashes.md) |
| Runtime | Python 3.12.10, PyTorch 2.11.0+cu128, CUDA 12.8, SQLite 3.49.1 |
| Output binding | `Hy3DExportMesh` node `99`, `filename_prefix=jobs/{job_id}/model`, `.glb` |

The live manifest verifier passed against the running instance after the
workflow hashes and allowlisted bindings were pinned. The two real serial jobs
and the adapter smoke job all produced textured GLBs without OOM; maximum
observed allocated VRAM was 4.832 GB on an 8151 MiB GPU.

Shape-only evidence from Phase 7 is deliberately excluded from the completion
claim. The real adapter path and the full shape-plus-texture workflow are the
only evidence used for this gate.

**Phase 9 verdict: PASS.**
