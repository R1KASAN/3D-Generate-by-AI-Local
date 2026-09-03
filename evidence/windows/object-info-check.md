# Manifest / `/object_info` Compatibility Verification (T062)

**Gate**: T062 - manifest/hash/`/object_info` compatibility verification
**Date/time and operator**: 2026-09-03, MetaHosP
**Host/environment**: LAPTOP-9PI3K9F7 (Windows), ComfyUI pinned instance on `127.0.0.1:8188`
**Script**: [`scripts/verify/verify_comfy_manifest.py`](../../scripts/verify/verify_comfy_manifest.py)
**Manifest**: [`workflows/hunyuan3d/workflow-manifest.json`](../../workflows/hunyuan3d/workflow-manifest.json)

## What the verifier checks

1. `comfyui_commit` matches `git rev-parse HEAD` of the installed ComfyUI.
2. Every `custom_nodes` entry with a non-null commit matches its installed
   repository's HEAD. Entries with a `null` commit are project-owned additions
   (see `local3d_smoke_nodes.py`) and are deliberately not tracked upstream.
3. Every declared node class - top-level `required_node_classes`,
   `smoke_workflow.required_node_classes`, and `output_binding.node_class` -
   is registered in the live `GET /object_info`.
4. Any pinned workflow-JSON SHA-256 matches the file on disk.

Failure behaviour is closed: a mismatch, an unreachable instance, an
unreadable/malformed manifest, or a manifest declaring no node classes all
exit non-zero.

## Positive case - pinned running instance

```bash
python scripts/verify/verify_comfy_manifest.py \
  workflows/hunyuan3d/workflow-manifest.json \
  --comfy-root "C:\Users\MetaHosP\ComfyUI"
```

```text
PASS: manifest workflows\hunyuan3d\workflow-manifest.json matches the running instance at http://127.0.0.1:8188
exit code: 0
```

## Negative cases - deliberate mismatch fixtures

Each fixture was a copy of the real manifest with exactly one field corrupted,
placed alongside the real manifest so relative workflow paths still resolved,
and removed after the run.

```text
=== bad-comfy-commit ===
ERROR: ComfyUI commit mismatch: manifest 0000000000000000000000000000000000000000, installed 345c9190497c82cff53e71fb4ae00d1e135a6542
exit code: 1

=== bad-node-commit ===
ERROR: custom node ComfyUI-Hunyuan3DWrapper commit mismatch: manifest deadbeefdeadbeefdeadbeefdeadbeefdeadbeef, installed 2609efa38f6a98292476f714839b7c1e5f9b699a
exit code: 1

=== bad-node-class ===
ERROR: node class not registered in running instance: Hy3DThisNodeDoesNotExist
exit code: 1

=== bad-workflow-hash ===
ERROR: smoke_workflow.api_workflow_sha256 mismatch: manifest ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff, file 02a21366f523885ee7c1603fa9bd7204964ce22e87999b50d737e2be1a63bd56
exit code: 1
```

Unreachable-instance case (fail closed rather than skip the live check):

```text
=== unreachable instance (wrong port) ===
ERROR: cannot reach http://127.0.0.1:9999/object_info
exit code: 1
```

## Verdict

`PASS` - the pinned running instance verifies clean, and every deliberate
commit, node-class, workflow-hash, and connectivity fault fails closed with a
specific, non-zero-exit error.

Follow-up closed the same day: the Hunyuan3D 2.1 checkpoint's `sha256` was
initially left `null` in the manifest's `models` entry. It has since been
computed over the installed 7.37 GB file and pinned as
`6b519fc7242f78e9b5f47ea4d55668fe3d944a2d27332f4ca68d29a6ff603f5e`.
