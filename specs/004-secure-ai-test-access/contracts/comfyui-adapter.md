# Contract: FastAPI to ComfyUI Generation Adapter

## Boundary

FastAPI is the durable job authority. ComfyUI is a private execution engine on
`http://127.0.0.1:8188`. Only the adapter may use ComfyUI routes or identifiers;
none are returned to the browser, routed by Caddy, stored in public URLs, or
written to public logs.

The mock and real adapters implement the same backend-facing meanings so all
job/API behavior can be exercised without the GPU.

## Backend-facing operations

### `submit(request) -> EngineHandle`

Input:

| Field | Rule |
|---|---|
| `job_id` | Opaque application UUID; used to isolate private engine input/output |
| `input_path` | Validated absolute path contained in this job's application upload directory |
| `output_dir` | Application-owned job work/output boundary; never supplied by a user |
| `workflow_revision` | Revision loaded from the verified workflow manifest, not a mock constant |
| `timeout_seconds` | Positive validated setting; 600 seconds by default |
| `idempotency_key` | Stable application Job ID for the one-attempt submission guard |

Preconditions:

1. The job is durably queued with its validated input.
2. The repository atomically reserves its one engine submission
   (`attempt_count=0` to reserved) before the adapter call.
3. The serial dispatcher owns the only GPU slot.
4. The workflow manifest, referenced workflow hash, bindings, output root, and
   required local runtime checks passed.

Behavior:

- Map only allowlisted input and output fields in the pinned workflow.
- Upload the input through ComfyUI's loopback `/upload/image` route using a
  server-generated filename derived from Job ID and verified extension.
- Submit the mapped workflow through `/prompt`.
- Return an opaque `EngineHandle`. Its `repr`, logs, API serialization, and
  exception messages must not expose the ComfyUI prompt ID.
- Never retry submission automatically when the outcome is uncertain. A failed
  call becomes a safe job failure or an operator-reconcilable uncertain state,
  not a second prompt.

### `inspect(handle) -> EngineObservation`

Behavior:

- Read `/history/{prompt_id}` first, then `/queue` when needed, using the private
  handle.
- Return one private adapter status: `queued`, `processing`, `succeeded`,
  `failed`, `cancelled`, or `unknown`.
- Return progress only when ComfyUI produced evidence for it.
- Use bounded retry only for idempotent status reads.
- On success, resolve candidates only beneath the configured ComfyUI output
  root and exactly the namespace `jobs/<job_id>`.
- A successful engine observation with zero, multiple, empty, outside-root, or
  invalid candidates does not complete the application job.

This call runs in the background observation loop. A public `GET /jobs/{id}`
must read durable SQLite state and must not synchronously wait for `inspect`.
Until the adapter interface is made fully async, the synchronous bridge is run
outside FastAPI's event-loop thread.

### `is_live() -> bool`

- Uses a short dedicated health timeout, independent of the generation timeout.
- Returns only a boolean/safe status to callers.
- Does not submit work, inspect a user job, download a model, or expose system
  details.
- A false result affects engine health and new admission but does not erase
  already accepted job state.

### `close()`

- Rejects new adapter calls.
- Closes the HTTP client and any private event loop/thread within a bounded
  shutdown interval.
- Is invoked after the job worker stops and before the FastAPI lifespan ends.
- Repeated close is safe.

## State translation

| ComfyUI/adapter observation | Durable application action | Public state |
|---|---|---|
| queued | Keep admitted job waiting/engine queued | `queued` |
| processing | Record start/progress when changed | `running` |
| succeeded with one valid published GLB | Atomically link asset and complete | `completed` |
| succeeded without a valid candidate | Record safe `invalid_output`/`missing_output` failure | `failed` |
| failed | Record allowlisted failure code/message | `failed` |
| cancelled | Record cancellation | `cancelled` |
| unknown before timeout | Keep latest durable state; retry only by bounded background policy | unchanged |
| unknown at timeout | Record `generation_timeout` | `failed` |

ComfyUI's term `processing` is private. Feature-004 public responses expose
`running`. Raw ComfyUI progress messages and exception strings are never public.

## Time and retry bounds

| Operation | Design bound |
|---|---|
| Health ping | Five-second outer bound, with a shorter client request timeout where supported |
| Upload/submit HTTP call | 30-second request bound; no automatic uncertain submission replay |
| Status/history/queue read | 30-second request bound with at most two retries and bounded backoff |
| Whole generation | Configurable positive bound; 600 seconds by default |
| Background observation cadence | One second default while non-terminal, adjustable only as a bounded setting |
| Adapter shutdown | Five seconds per client/thread close stage, followed by safe process shutdown handling |

The whole-generation bound begins when engine submission is accepted, survives
browser disconnection, and ends in a safe terminal failure if exceeded. Target
RTX 5070 measurements may support an approved configuration change; they do not
change the public API contract or promise a generation SLA.

## Workflow manifest and readiness

The real adapter uses
`workflows/hunyuan3d/workflow-manifest.json`, currently identifying:

- workflow `hunyuan3d-textured-glb`;
- revision `hunyuan3d-textured-glb-2026-09-03`;
- ComfyUI 0.34.0 at the pinned commit;
- the hash-pinned API workflow and allowlisted `LoadImage` input binding;
- `Hy3DExportMesh` output prefix `jobs/{job_id}/model` with `.glb` extension;
- pinned node/model/runtime requirements for the target RTX 5070.

Startup/readiness verifies, without logging secrets or model contents:

1. manifest structure and revision;
2. API workflow file hash and allowlisted bindings;
3. required ComfyUI node classes using loopback engine metadata;
4. required model presence and approved integrity evidence;
5. readable input and writable contained output roots;
6. compatible Python/PyTorch/CUDA/GPU capability from the pinned baseline;
7. ComfyUI health and a safe, bounded readiness result;
8. SQLite runtime/journal safety separately at the application boundary.

Failure is fail-closed. Real mode never silently falls back to the mock adapter.
The public health API returns only `ok`, `degraded`, or `unavailable`; detailed
operator evidence remains local.

## Output publication

1. Resolve exactly one non-empty `.glb` under the job-specific ComfyUI output
   directory.
2. Prove the resolved path remains within the configured output root and does
   not traverse or follow an unsafe link.
3. Validate GLB version/structure plus the required mesh, UV, material, and
   texture content.
4. Hash and copy/write to a same-volume temporary application path.
5. Atomically replace `storage/outputs/<job_id>/model.glb`.
6. Persist the output asset and `completed` transition in the job store.
7. Only then expose model/download URLs.

Any failure before step 6 leaves no public completed result. Quarantine and
intermediate paths are never public.

## Restart and uncertain work

- Jobs with no reserved engine attempt may be requeued in durable FIFO order.
- A reserved or running job is not resubmitted automatically after API or
  Notebook restart.
- Reattachment is allowed only if an exact stored handle and a tested ComfyUI
  history/queue query prove ownership. The MVP default is a durable
  `restart_recovery` failure.
- The operator health/recovery procedure checks for a possible orphan prompt
  and interrupts or quarantines it. Its output can never be attached to another
  job.
- A ComfyUI restart that loses its queue causes explicit safe failures; it never
  converts unknown work to completed.

## Security assertions

- Base URL validation rejects non-loopback ComfyUI hosts.
- Caddy has no upstream or route to port 8188.
- Workflow input and output fields are allowlisted; a client cannot send an
  arbitrary ComfyUI graph, node, model, path, or output prefix.
- Engine handles, workflow bodies, filesystem paths, model metadata, GPU
  details, and raw errors do not appear in the public API or project logs.
- Tests cover malicious paths, wrong-job candidates, duplicate candidates,
  empty/invalid GLB, stalled status reads, duplicate submission prevention,
  timeout, cancellation, shutdown, and restart reconciliation.
