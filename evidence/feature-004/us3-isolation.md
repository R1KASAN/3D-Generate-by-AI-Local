# US3 Multi-user Isolation Evidence

## Five-user local trial

- Executed: `uv run --project apps/api pytest apps/api/tests/integration/test_two_user_queue.py -q`
- Result: **2 passed in 3.17s**
- The five-user case admitted five independent jobs and asserted five distinct
  capability tokens, storage roots, result byte streams, and SHA-256 hashes.
- The observed maximum was one `running` job while other accepted work remained
  `queued`; all five jobs completed through the serial mock adapter.
- A first-user token used against the second user's download returned the
  uniform `404` boundary response.

## Controlled two-job real RTX trial

The existing target-hardware evidence at
`evidence/windows/two-job-serial.md` records two approved Hunyuan3D textured-GLB
executions on the RTX 5070 Laptop GPU. It proves:

- maximum observed active GPU jobs: **1**;
- distinct job-scoped output paths;
- distinct sizes and SHA-256 hashes;
- no overwrite after the second job;
- one valid textured GLB per job.

The recorded real result hashes are retained in that evidence file. Raw job
tokens, ComfyUI prompt identifiers, user content, and generated model bytes are
not duplicated here.

## Verdict

**PASS** - the local five-user ownership/queue trial and the controlled two-job
real-GPU serial trial satisfy T057 without repeating expensive GPU work.
