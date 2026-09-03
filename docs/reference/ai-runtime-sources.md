# Curated AI Runtime Sources

**Purpose**: Owner-provided references retained for contextual use in the Local
3D Generative AI Server. This is a source register, not an installation guide,
dependency lockfile, approval to run third-party scripts, or evidence that a
runtime is compatible with the target Windows server.

**Usage rule**: Consult the relevant source when a task reaches its matching
phase. Before an artifact is installed or adopted, record its exact revision,
license, compatibility evidence, and validation result in the workflow manifest
and gate evidence. Do not auto-update from these links.

## Source register

| Source | Use when | Boundary |
|---|---|---|
| [ComfyUI installation](https://github.com/Comfy-Org/ComfyUI?tab=readme-ov-file#installing) | Windows ComfyUI setup, supported installation options, and official runtime guidance | Pin the chosen ComfyUI revision; do not expose its port publicly. |
| [ComfyUI-Manager](https://github.com/Comfy-Org/ComfyUI-Manager) | Manually discovering or installing a custom node during controlled Windows validation | Manager must not perform unattended production updates. Every selected node is pinned and verified separately. |
| [NVIDIA CUDA Toolkit 12.8 archive for Windows](https://developer.nvidia.com/cuda-12-8-0-download-archive?target_os=Windows&target_arch=x86_64&target_version=11&target_type=exe_local) | Checking a CUDA 12.8 prerequisite for a specific wrapper/native wheel | Installing the toolkit does not by itself establish PyTorch/driver compatibility; verify with `nvidia-smi` and the actual Python environment. Updated 2026-09-03 from 12.6 to 12.8, the minimum version with Blackwell (`sm_120`) kernel support — see research.md §5. |
| [ComfyUI-Hunyuan3DWrapper](https://github.com/kijai/ComfyUI-Hunyuan3DWrapper?tab=readme-ov-file) | Building the pinned, full shape-plus-texture Hunyuan workflow required for the MVP GLB | Record commit, dependency/model hashes, license, nodes, and output contract. A successful shape-only run is insufficient. |
| [Tencent Hunyuan3D-2.1](https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1/tree/main) | Native model/runtime inspection and the Windows GPU smoke gate | Treat it as a source for validation/research. It does not silently replace the pinned final textured workflow. |
| [ComfyUI img2img example workflow](https://comfyanonymous.github.io/ComfyUI_examples/img2img/img2img_workflow.png) | Learning the visual/API workflow graph pattern during development | It is an img2img example, not the Hunyuan3D production workflow and not an acceptance artifact. |
| [DreamingAI WebSocket API example](https://github.com/Nuked88/DreamingAI/blob/main/dreaminAI_websockets_api_example.py) | Studying an external Python-to-ComfyUI WebSocket integration pattern | Do not copy it wholesale. The backend must preserve the documented `GenerationAdapter` contract; browser clients never connect to ComfyUI. |

## Application points

- Windows AI setup: ComfyUI install source, CUDA archive only when the pinned
  runtime requires it, then GPU/runtime evidence.
- Workflow validation: wrapper and Hunyuan3D sources, then immutable API
  workflow JSON and a completed textured-GLB validation report.
- ComfyUI API adapter: official ComfyUI API documentation plus the DreamingAI
  example only as a non-authoritative pattern reference.
- Workflow education: img2img example as a graph-learning aid, never as the
  deployed Hunyuan workflow.

## Governing project artifacts

- [Feature plan](../../specs/001-local-3d-generation/plan.md)
- [Research decisions](../../specs/001-local-3d-generation/research.md)
- [Generation adapter contract](../../specs/001-local-3d-generation/contracts/generation-adapter.md)
- [ComfyUI workflow manifest contract](../../specs/001-local-3d-generation/contracts/comfyui-workflow-manifest.md)
- [Quickstart and verification gates](../../specs/001-local-3d-generation/quickstart.md)

If a source conflicts with the constitution, feature specification, or a locked
owner decision, those project artifacts govern until the owner approves an
amendment.

