# US2 Recovery Evidence

**Feature:** `001-local-3d-generation`  
**Environment:** macOS, CPython 3.12.12, SQLite, deterministic mock adapter  
**Scope:** queue/progress/failure/restart behavior only; no Windows, GPU,
ComfyUI, LAN, or public-network claim.

## Verification

```text
uv run --project apps/api pytest apps/api/tests/contract/test_job_status_and_failures.py apps/api/tests/integration/test_adapter_recovery.py apps/api/tests/integration/test_job_lifecycle.py apps/api/tests/unit/test_job_state.py
27 passed

npm --prefix apps/web run test
3 test files passed, 8 tests passed

npm --prefix apps/web run typecheck
Passed (tsc --noEmit)
```

The adapter matrix covered timeout, disconnect, uncertain result, cancellation,
missing output, and ordinary failure. Every failure response used a safe public
message, never exposed an engine identifier or path, and never returned a model
URL. A restart with a processing job produced `restart_recovery` and the new
adapter recorded zero submissions, proving no automatic duplicate submission.

The browser status hook refreshes immediately, then after 2 seconds and backs
off to 5–10 seconds, stopping on completed, failed, or cancelled states. Queue
position and progress remain explicitly unavailable when the engine reports no
value.

## Verdict

`PASS` — US2 mock lifecycles are terminal or safely reconciled, refresh-safe,
and incomplete output is never served.
