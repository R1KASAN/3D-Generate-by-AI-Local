# Contract: GenerationAdapter

The backend owns the public job contract and durable lifecycle. Both the macOS
mock and Windows ComfyUI implementations conform to this interface.

## Interface

```text
submit(request: GenerationRequest) -> EngineHandle
inspect(handle: EngineHandle) -> EngineObservation
cancel(handle: EngineHandle) -> CancelObservation
reconcile(handle: EngineHandle) -> EngineObservation
```

### `GenerationRequest`

- opaque application Job ID;
- absolute trusted input path resolved inside that job's storage;
- trusted output directory and prefix created by the backend;
- pinned workflow revision;
- bounded timeout and idempotency key.

It never contains user-controlled paths or public capability tokens.

### `EngineHandle`

Opaque adapter-private data sufficient to inspect one execution. It may contain a
ComfyUI `prompt_id`, but the backend never serializes it into a public response.

### `EngineObservation`

One of:

- `queued` with nullable progress;
- `processing` with nullable evidence-backed progress;
- `succeeded` with one candidate local GLB path;
- `failed` with an internal cause and mapped safe error code;
- `cancelled`;
- `unknown`, requiring fail-safe reconciliation rather than duplicate submission.

## Behavioral requirements

1. `submit` is called only after the durable job is committed as queued.
2. One dispatcher calls `submit`; supported GPU concurrency is exactly one.
3. Repeating an idempotency key must not create conflicting published outputs.
4. Timeout or connection loss returns an uncertain observation and triggers
   reconciliation; it does not automatically resubmit.
5. The adapter may write only inside the assigned engine/job output prefix.
6. Success requires exactly one candidate GLB. Zero or multiple candidates fail.
7. The application validates GLB structure, mesh, UVs, material, and texture
   before atomically publishing `storage/outputs/<job_id>/model.glb`.
8. Adapter exceptions, paths, workflow node IDs, and stack traces are logged only
   in sanitized operator context and never returned to the browser.
9. `cancel` is idempotent. Cancellation failure cannot change an already terminal
   application state.
10. On startup, every persisted `processing` job is reconciled before new dispatch.

## Mock adapter

- Uses a repository fixture with a known-good textured GLB.
- Advances through deterministic queued/processing/succeeded observations.
- Supports configured failure, missing-output, timeout, and reconnect scenarios.
- Copies into the assigned candidate location, then relies on the same application
  validation/publication path as the real adapter.
- Must not bypass token, storage, state-machine, or cleanup code.

## ComfyUI adapter

- Uses only loopback `http://127.0.0.1:8188` and internal `/ws`.
- Submits a pinned API-format workflow through `/prompt`.
- Injects only allowlisted fields: trusted input path/reference and server-created
  `jobs/<job_id>/model` output prefix.
- Reconciles via `/queue` and `/history/{prompt_id}` after disconnect/restart.
- Resolves output only inside `ComfyUI/output/jobs/<job_id>/`.
- Refuses startup/submission when required node classes, workflow hash, model
  files, or runtime compatibility do not match the workflow manifest.

## Shared contract tests

Both adapters must pass the same tests for:

- submit and observe success;
- deterministic failure;
- missing and multiple outputs;
- timeout/unknown result without duplicate execution;
- idempotent cancellation;
- restart reconciliation;
- isolation across two Job IDs;
- no leakage of engine identifiers;
- GLB validation and atomic publication.

The real adapter tests may be hardware-gated, but their absence must remain a
visible blocker rather than being replaced by mock evidence.

