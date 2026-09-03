# Two-Job Serial Isolation Evidence (T077)

**Date/time:** 2026-09-03 (UTC)

**Host/runtime:** `LAPTOP-9PI3K9F7`; RTX 5070 Laptop GPU, 8151 MiB; ComfyUI
`0.34.0`; pinned API workflow; one loopback execution queue.

Both jobs were submitted only after the prior queue was empty. The second
submission was refused by the runner if any job was already running or pending.
Each output prefix included the server-created UUID and each job directory
contained exactly one non-empty GLB.

The application `ComfyGenerationAdapter` was also exercised with the pinned
workflow immediately afterward (job
`dd365728-1cad-4f65-adb5-9de4f523b735`; see
[textured-generation-1.md](textured-generation-1.md)). It returned one
job-scoped candidate with no public engine identifier, confirming that the
mapper, queue serialization, and output resolver used by the application agree
with the direct API observations below.

| Job ID | Input | Output path | Duration | Peak VRAM | Size | SHA-256 | GLB validation |
|---|---|---|---:|---:|---:|---|---|
| `e0787447-629f-4678-a7a1-85dced07f4b1` | `valid-reference.png` | `output/jobs/e0787447-629f-4678-a7a1-85dced07f4b1/model_00001_.glb` | 124.97 s | 4.832 GB | 3,665,992 | `00d7342f82c904233d9748e6dabf575dde866cc25dc40b40b457d0c4c02f200e` | PASS |
| `4a06f07b-a769-4583-96d3-59ace105db89` | `valid-reference.jpg` | `output/jobs/4a06f07b-a769-4583-96d3-59ace105db89/model_00001_.glb` | 113.16 s | 4.832 GB | 2,221,016 | `ced8dcec23e54926586d7db11485a05b2552d43f3b5845bcea4310997eb35ab1` | PASS |

Retained artifacts: [textured-job-e0787447.glb](artifacts/textured-job-e0787447.glb),
[textured-job-4a06f07b.glb](artifacts/textured-job-4a06f07b.glb).

## Isolation and concurrency checks

- Maximum observed active GPU job count: **1**. Queue snapshots showed one
  running item while each job executed and zero pending items; the second job
  was not submitted until the first returned success.
- Each job directory contained exactly one `.glb`; no symlinks or cross-job
  links were present.
- The two output hashes and byte sizes differ, and neither output path points
  into the other job's directory.
- The output prefixes were `jobs/<job-id>/model`; no global `3D/` or newest-file
  discovery was used.
- No overwrite was observed: the pre/post file snapshot for each job remained
  one file, and the first job's bytes/hash remained unchanged after the second.
- Both outputs passed the same structural validator with mesh, UV, material,
  texture, and image requirements.

**Verdict: PASS.**
