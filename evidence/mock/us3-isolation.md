# US3 Queue and Isolation Evidence

**Feature:** `001-local-3d-generation`  
**Environment:** macOS, CPython 3.12.12, SQLite, deterministic mock adapter  
**Scope:** serial mock queue and same-job authorization only; no Windows,
GPU, ComfyUI, LAN, or public-network claim.

## Verification

```text
uv run --project apps/api pytest apps/api/tests/unit/test_serial_dispatcher.py apps/api/tests/security/test_job_isolation.py apps/api/tests/integration/test_duplicate_safety.py apps/api/tests/integration/test_two_user_queue.py
8 passed
```

The two-user API scenario observed the first job as `queued → processing →
completed` while the second remained queued until the first released the sole
active dispatcher slot, then completed in FIFO order. The adapter submission
count was exactly 2 for 2 distinct jobs. Each job used a different UUID-derived
storage root and the swapped-token, guessed-ID, traversal, and symlink escape
checks returned no cross-job data.

Duplicate adapter submission with one idempotency key reused one opaque private
handle (`submission_count == 1`); conflicting keys were rejected by the
process-local guard. No prompt IDs or paths appeared in public responses.

## Verdict

`PASS` — one active mock execution, FIFO waiting, isolated folders, uniform
authorization misses, and duplicate-safe adapter submission are verified.
