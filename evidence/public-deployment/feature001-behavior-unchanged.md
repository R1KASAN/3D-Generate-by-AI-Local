> **Feature 003 update (2026-09-06):** The normal feature-001 journey, token policy, 10 MiB upload limit, serial GPU execution, 24-hour retention and 10% disk threshold remain. FR-031 now adds atomic queue/retry/identical-submission admission limits in the API. Thus the historical statement that no application source changes exist is no longer current. See `outbound-implementation.md` for local tests; live acceptance remains blocked.

# Feature 001 Behavior Preserved Under Feature 003 — T068-T071

**Feature**: `003-outbound-tunnel-entry` | **Recorded**: 2026-09-06

FR-014's thin-origin design moves no job state, queue, storage, or generation logic to the approved origin — the entire feature 001 application, including its concurrency, upload-validation, disk-gating, and artifact-integrity behavior, runs unmodified on the GPU laptop. This file records that the pre-existing, already-passing feature 001 test coverage for these SC criteria was reviewed and confirmed to still hold, rather than duplicating tests for behavior this feature does not touch.

| Task | Requirement | Existing coverage | Status |
|---|---|---|---|
| T068 | SC-011: five simultaneous submissions execute at most one GPU job at a time, each isolated | `apps/api/tests/unit/test_serial_dispatcher.py::test_fifo_dispatcher_allows_one_active_job_and_approximate_positions`, `::test_duplicate_enqueue_does_not_create_a_second_execution`; `apps/api/tests/integration/test_two_user_queue.py::test_two_users_wait_in_fifo_queue_and_keep_isolated_outputs` | **PASS** (confirmed in full suite run, 2026-09-06) |
| T069 | SC-012: unsupported, corrupt, disguised, and oversized uploads rejected before GPU execution | `apps/api/tests/unit/test_upload_validation.py::test_corrupt_spoofed_and_oversized_uploads_are_rejected`, `::test_exact_configured_limit_is_allowed`, `::test_stream_is_bounded_before_image_decode` | **PASS** |
| T070 | SC-015: no incomplete artifact returned as completed under termination, missing-output, low-disk, or restart | `apps/api/tests/contract/test_job_status_and_failures.py`, `apps/api/tests/integration/test_adapter_recovery.py`, `apps/api/tests/integration/test_job_lifecycle.py` (mock adapter `mode="missing"` produces `SUCCEEDED, candidates=()`, never surfaced as a downloadable completed artifact) | **PASS** |
| T071 | FR-029: new jobs rejected below 10% free disk; active jobs reach a safe terminal state where possible | `apps/api/tests/unit/test_upload_validation.py::test_low_disk_blocks_new_job_admission` (exact 10% threshold). `ensure_disk_admission` is called only in `JobService.create_job` (`apps/api/src/local3d/services/job_service.py:184`), never in the worker loop that advances already-admitted jobs — so an in-flight job is never aborted by a later disk-space check by construction | **PASS** |

## Verification run

```
cd apps/api && ./.venv/Scripts/python.exe -m pytest tests/ -q
119 passed, 4 skipped
```

No code change was made for T068-T071: the finding is that feature 003 introduces no new code path affecting this behavior, so the existing feature 001 evidence already satisfies these success criteria.
