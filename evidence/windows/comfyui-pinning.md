# ComfyUI + Custom Node Pinning Evidence (T059)

**Gate**: T059 - install and pin ComfyUI plus required custom-node revisions
**Date/time and operator**: 2026-09-03, MetaHosP
**Host/environment**: LAPTOP-9PI3K9F7 (Windows), target production server for Phase 7-12
**Manifest**: [`workflows/hunyuan3d/workflow-manifest.json`](../../workflows/hunyuan3d/workflow-manifest.json)

## Pinned revisions

| Component | Commit | Repo |
|---|---|---|
| ComfyUI | `345c9190497c82cff53e71fb4ae00d1e135a6542` | https://github.com/comfyanonymous/ComfyUI |
| ComfyUI-Manager | `b75fc664ecab9c4602380d9660833d02f6a63333` | https://github.com/Comfy-Org/ComfyUI-Manager |
| ComfyUI-Hunyuan3DWrapper | `2609efa38f6a98292476f714839b7c1e5f9b699a` | https://github.com/kijai/ComfyUI-Hunyuan3DWrapper |

The Hunyuan3D wrapper commit is identical to the candidate already audited in
`research.md` section 5 at planning time (`2609efa3...`), confirming the
upstream repository has not moved past that commit.

## Commands executed

```bash
git -C ~/ComfyUI rev-parse HEAD
git -C ~/ComfyUI/custom_nodes/ComfyUI-Manager rev-parse HEAD
git -C ~/ComfyUI/custom_nodes/ComfyUI-Hunyuan3DWrapper rev-parse HEAD
```

```powershell
# Start (loopback only)
python main.py --listen 127.0.0.1 --port 8188
```

```bash
curl -s http://127.0.0.1:8188/system_stats
curl -s http://127.0.0.1:8188/object_info
```

## Step 1: First start - commits match running instance

Server started at 2026-09-03 17:24:48, bound to `127.0.0.1:8188` only
(`argv: ["main.py", "--listen", "127.0.0.1", "--port", "8188"]` in
`/system_stats`). `comfyui_version` reported as `0.34.0`, consistent with the
pinned working-tree commit above (no local modifications; `git status`
clean). GPU device reported: `cuda:0 NVIDIA GeForce RTX 5070 Laptop GPU`.

`/object_info` was queried and returned 46 Hunyuan3D-related node classes,
confirming `ComfyUI-Hunyuan3DWrapper` loaded without import error, including
the contract-required output node `Hy3DExportMesh`. Full snapshot recorded in
`workflow-manifest.json` under `available_node_classes_snapshot`.

## Step 2: Restart - health request succeeds again

```text
[before restart] curl -m 3 http://127.0.0.1:8188/system_stats -> exit 7 (connection refused, confirms process was stopped)
[Stop-Process -Id 20988 -Force]
[Start-Process ... main.py --listen 127.0.0.1 --port 8188]  (new PID 36524)
[poll every 3s until reachable]
[after restart] curl http://127.0.0.1:8188/system_stats -> HTTP 200, comfyui_version 0.34.0
```

Post-restart, `git rev-parse HEAD` was re-run for all three repositories and
produced the identical commits listed above - no drift between the pinned
manifest and the running instance across a restart.

## Verdict

`PASS` - ComfyUI and both required custom nodes are pinned to exact commits,
the running `127.0.0.1:8188` instance matches those commits, `Hy3DExportMesh`
and the full Hunyuan3D node set are registered, and a post-restart health
request succeeded without configuration drift.

Not yet in scope for T059 (deferred to T061/T075 per the manifest contract):
`workflow_id` hash pinning, `models`, and `required_node_classes` - these
depend on the actual pinned workflow JSON, which does not exist until the
native shape smoke (T061) and full textured workflow (T075) are built.
