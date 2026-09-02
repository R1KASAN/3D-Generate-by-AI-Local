# Contract: ComfyUI/Hunyuan3D Workflow Manifest

Every production workflow release contains both editable ComfyUI JSON and
API-format JSON plus a machine-readable `workflow-manifest.json`.

## Required manifest fields

```json
{
  "workflow_id": "hunyuan3d-textured-glb",
  "workflow_revision": "owner-approved-semver-or-hash",
  "api_workflow_sha256": "sha256",
  "editable_workflow_sha256": "sha256",
  "comfyui_commit": "git-commit",
  "custom_nodes": {
    "ComfyUI-Hunyuan3DWrapper": "git-commit"
  },
  "runtime": {
    "python": "3.12.x",
    "pytorch": "2.6.x",
    "cuda": "12.6",
    "sqlite": "runtime-version"
  },
  "models": [
    {"name": "artifact", "path": "trusted-relative-path", "sha256": "sha256"}
  ],
  "required_node_classes": ["class-name"],
  "input_bindings": ["allowlisted-node-and-field"],
  "output_binding": {
    "node_class": "Hy3DExportMesh",
    "prefix_pattern": "jobs/{job_id}/model",
    "expected_extension": ".glb"
  },
  "licenses": [
    {"artifact": "license-file", "sha256": "sha256", "reviewed_at": "UTC"}
  ]
}
```

Actual node class names and model filenames must be exported and verified from
the pinned Windows installation; placeholders are not a production manifest.

## Reproducibility rules

- Pin exact Git commits for ComfyUI and every custom node. No automatic update.
- Hash workflow JSON, model/checkpoint files, native wheels, and license files.
- Store Python/package lock evidence separately for the ComfyUI environment.
- Record GPU model, driver, VRAM, and successful fixture hashes in gate evidence.
- Any hash/version change creates a new workflow revision and repeats validation.

## Startup compatibility check

Before accepting real-adapter jobs:

1. Confirm the pinned manifest parses and hashes match.
2. Query ComfyUI `/object_info` and verify every required node class and binding.
3. Verify all model artifacts and native dependencies exist with matching hashes.
4. Verify the SQLite version/journal-mode safety gate for application persistence.
5. Confirm the application-created ComfyUI job output root is writable and does
   not escape the configured output directory.
6. Fail readiness closed with a safe operator error on any mismatch.

## Execution and output contract

1. Backend creates the Job ID, job directory, and sanitized output prefix.
2. Adapter loads immutable API-format workflow JSON and changes only allowlisted
   input and output binding values.
3. Submit to `/prompt`; persist returned `prompt_id` only as internal metadata.
4. Observe internal WebSocket messages; reconcile with `/queue` and `/history`.
5. Treat execution success as provisional because `Hy3DExportMesh` may return a
   string path rather than a normal UI output entry.
6. After success, enumerate only `ComfyUI/output/jobs/<job_id>/` and require
   exactly one `.glb` matching the prefix.
7. Validate non-empty GLB, parseability, mesh primitives, UV attributes, material,
   and texture reference/content before application publication.
8. Move a validated result atomically. Quarantine invalid or ambiguous output.

## Mandatory Windows evidence gates

- `nvidia-smi` and PyTorch CUDA/device/VRAM evidence.
- Native Hunyuan3D 2.1 shape smoke artifact (hardware only, not MVP completion).
- Pinned Hunyuan3D 2.0 shape-plus-texture workflow artifact.
- Two serial jobs with distinct inputs/directories and no overwrite or OOM.
- GLB validation report proving mesh, UV, material, and texture.
- API-only submission without clicking ComfyUI UI.
- Engine failure, missing output, timeout, and restart reconciliation evidence.
- Exact commits, package lock, model hashes, and license review record.

Public deployment remains blocked until the owner accepts the license/territory
constraints for the actual pinned artifacts.

