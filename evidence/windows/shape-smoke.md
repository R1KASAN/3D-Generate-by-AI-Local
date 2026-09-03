# Native Hunyuan3D 2.1 Shape Smoke Evidence (T061)

**Gate**: T061 - native Hunyuan3D 2.1 shape smoke workflow
**Date/time and operator**: 2026-09-03, MetaHosP
**Host/environment**: LAPTOP-9PI3K9F7 (Windows), RTX 5070 Laptop GPU, 8 GB VRAM
**Scope**: Hardware/model smoke signal only, per research.md section 5 -
**not** MVP textured-GLB completion (that is T075, using Hunyuan3D 2.0).

## Model

- Checkpoint: `tencent/Hunyuan3D-2.1/hunyuan3d-dit-v2-1/model.fp16.ckpt`
- Size: 7,366,389,768 bytes (7.37 GB), downloaded from
  `https://huggingface.co/tencent/Hunyuan3D-2.1`, no authentication wall
- Installed at `ComfyUI/models/diffusion_models/hunyuan3d-dit-v2-1-model.fp16.ckpt`
- Config: wrapper-bundled `configs/dit_config_2_1.yaml` (HunYuanDiTPlain, MoE,
  depth 21, matches the 2.1 architecture)

## Workflow files

- Editable: [`workflows/hunyuan3d/editable/hunyuan3d-21-shape-smoke.json`](../../workflows/hunyuan3d/editable/hunyuan3d-21-shape-smoke.json)
- API: [`workflows/hunyuan3d/api/hunyuan3d-21-shape-smoke.json`](../../workflows/hunyuan3d/api/hunyuan3d-21-shape-smoke.json)
- Input fixture: `fixtures/inputs/valid-reference.png`, copied into ComfyUI's
  input folder as `hunyuan3d-smoke-input.png`

Graph: `LoadImage -> Hy3D21ShapeSmokeOffloadMeshGen -> Hy3DExportMesh`. All
submissions were made via `POST /prompt` against `127.0.0.1:8188` - no
ComfyUI UI clicks.

## Hardware finding and documented deviation

The wrapper's own `Hy3D_2_1SimpleMeshGen` node loads the full model directly
onto the GPU (`from_single_file(..., device='cuda')` with no offload), which
needs ~7.13 GiB. On this 8 GB card that consistently produced
`torch.OutOfMemoryError` (`Free according to CUDA: 0 bytes`) immediately
after model load, reproduced identically across a clean process restart and
with `--lowvram`, ruling out fragmentation or another GPU consumer as the
cause - see command log below.

Rather than treat this as an unconditional block, a small **project-owned**
custom node was added at
[`C:\Users\MetaHosP\ComfyUI\custom_nodes\local3d_smoke_nodes.py`](../../../../../ComfyUI/custom_nodes/local3d_smoke_nodes.py)
(not part of, and does not modify, the pinned
`ComfyUI-Hunyuan3DWrapper@2609efa3...` commit). It reuses the exact same
pinned `Hunyuan3DDiTFlowMatchingPipeline` class and config, but:

1. Loads the pipeline on CPU first (`device="cpu"`).
2. Supplies a `pipeline.components` dict (vae/model/conditioner/image_processor)
   so the pipeline's existing `enable_model_cpu_offload()` method - present in
   the pinned wrapper but never called by any of its own nodes - can be used;
   this bespoke class isn't a diffusers `DiffusionPipeline` subclass and has
   no `.components` property of its own.
3. Restores `pipeline.device` to the GPU device after offload setup, because
   `enable_model_cpu_offload()` leaves that attribute pinned to `cpu` (the
   resident device) rather than exposing a dynamic execution-device property.
   Code that creates a fresh tensor via `device=self.device` - specifically
   the classifier-free-guidance unconditional-embedding branch, which calls a
   plain method rather than a hooked `forward()` - was landing on CPU while
   the hooked conditioner's real forward output landed on GPU, causing a
   `RuntimeError` device mismatch at concatenation. Restoring the attribute
   fixes this without touching hook behavior, which is keyed off the modules
   themselves, not this attribute.

**Reason**: fit the pinned 2.1 fp16 model on an 8 GB GPU for the purposes of
this hardware smoke gate. **Risk**: shape-smoke scope only; not used for the
MVP textured-GLB workflow (T075), which is a separate Hunyuan3D 2.0 pipeline.
**Review trigger**: revisit if the target server's GPU changes, or when
upstream `ComfyUI-Hunyuan3DWrapper` adds native offload support to its own
nodes.

## Command log (chronological, all via `python -c` against the venv + curl)

```text
1. Submit with Hy3D_2_1SimpleMeshGen (upstream node, no offload)
   -> ModuleNotFoundError: omegaconf          [pip install omegaconf]
2. Resubmit
   -> ModuleNotFoundError: rembg              [pip install rembg]
3. Resubmit
   -> ModuleNotFoundError: timm               [pip install timm torchdiffeq]
4. Resubmit
   -> torch.OutOfMemoryError (7.13 GiB allocated, 0 bytes free)
   nvidia-smi during failure: 7246 MiB / 8151 MiB used
5. Stop-Process; confirm VRAM fully released (0 MiB used); restart; resubmit
   -> identical OutOfMemoryError (rules out fragmentation)
6. Swap onnxruntime-gpu -> onnxruntime (CPU) for rembg, restart, resubmit
   -> identical OutOfMemoryError (rules out rembg as the consumer)
7. Restart with --lowvram, resubmit
   -> identical OutOfMemoryError (ComfyUI's global vram mode doesn't reach
      this pipeline's own unmanaged .to(device) call)
8. Tried modular Hy3DModelLoader + Hy3DGenerateMesh + Hy3DVAEDecode chain
   -> KeyError: 'model' (this loader targets the separate Hunyuan3D 2.0
      pipeline class - a different checkpoint format - not 2.1; abandoned)
9. Added local3d_smoke_nodes.py (CPU-offload variant), restart, resubmit
   -> AttributeError: 'Hunyuan3DDiTFlowMatchingPipeline' object has no
      attribute 'components'                 [supplied components dict]
10. Restart, resubmit
    -> RuntimeError: tensors on cuda:0 and cpu [restored pipeline.device
       to GPU after offload setup]
11. Restart, resubmit
    -> SUCCESS
```

## Successful submission

```bash
curl -s -X POST http://127.0.0.1:8188/prompt -H "Content-Type: application/json" \
  -d @workflows/hunyuan3d/api/hunyuan3d-21-shape-smoke.json
# {"prompt_id": "1dedc9d8-3418-41d5-a7fe-73e972ff3932", "number": 0, "node_errors": {}}

curl -s http://127.0.0.1:8188/history/1dedc9d8-3418-41d5-a7fe-73e972ff3932
```

## Observed result

```text
status_str: success
completed: True
execution_start:   1788432840792
execution_success: 1788432955037   (114.2 seconds end to end)
```

Output file on disk:
`C:\Users\MetaHosP\ComfyUI\output\smoke\hunyuan3d-21-shape-smoke_00001_.glb`

```text
size: 5,593,048 bytes
sha256: 8f3c9c3ce26a6f019131907cc555b5d18bfa2971df56a790d6c7cb9ecb8b15d8
```

Copy retained at
[`evidence/windows/artifacts/hunyuan3d-21-shape-smoke.glb`](artifacts/hunyuan3d-21-shape-smoke.glb)
(identical SHA-256).

Parsed with `trimesh.load(...)`:

```text
<class 'trimesh.scene.scene.Scene'>
geometry_0 vertices: 155342 faces: 310680
```

## Verdict

`PASS` (hardware/model smoke signal only) - one API-submitted job against the
pinned Hunyuan3D 2.1 checkpoint produced exactly one non-empty, parseable
shape-only GLB with a real triangle mesh. **This is explicitly not MVP
textured-GLB completion** - no texture, material, or UV data was requested or
produced, consistent with research.md section 5 ("Native Hunyuan3D 2.1 shape
generation is only an earlier hardware smoke test").

Carried-forward finding for T075 planning: the wrapper's un-offloaded
loading pattern does not fit this 8 GB GPU even for shape-only generation.
The full textured pipeline (Hunyuan3D 2.0, separate model/loader) will need
either equivalent offload handling or more VRAM headroom, and should not be
assumed to fit by default.
