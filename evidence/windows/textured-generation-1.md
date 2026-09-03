# Real Textured Generation Evidence (T075)

**Date/time:** 2026-09-03 (UTC)

**Host:** `LAPTOP-9PI3K9F7`, Windows 11, NVIDIA GeForce RTX 5070 Laptop GPU
(8151 MiB), ComfyUI `0.34.0` on `127.0.0.1:8188`.

## Submission

The pinned API workflow was submitted through the application
`ComfyGenerationAdapter` after `WorkflowMapper.from_manifest` verified the
manifest and both workflow hashes. The adapter uploaded
`fixtures/inputs/valid-reference.png`, injected only the allowlisted image field
and the server-owned output prefix, and returned an opaque handle with
`public_id=None`.

| Field | Observed |
|---|---|
| Job ID | `dd365728-1cad-4f65-adb5-9de4f523b735` |
| Input | `fixtures/inputs/valid-reference.png` |
| Output prefix | `jobs/dd365728-1cad-4f65-adb5-9de4f523b735/model` |
| Candidate directory | `C:\Users\MetaHosP\ComfyUI\output\jobs\dd365728-1cad-4f65-adb5-9de4f523b735` |
| Adapter terminal observation | `succeeded`, one candidate |
| Generation duration | 127.89 seconds |
| Peak allocated VRAM | 4.615 GB; peak reserved 4.656 GB |
| Candidate size | 3,737,948 bytes |
| Candidate SHA-256 | `b2c806a54a070ae9ea26b4bc2ce44edf3f8344ccbb999523fd196fecb635dba1` |
| Retained artifact | [textured-adapter-dd365728.glb](artifacts/textured-adapter-dd365728.glb) |

## Result

The job directory contained exactly one non-empty `.glb`. The structural
validator passed mesh, UV, material, and texture requirements; the detailed
report is in [textured-glb-validation.md](textured-glb-validation.md).

**Verdict: PASS.**
