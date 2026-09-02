# Phase 2 Foundation Evidence

**Feature**: `001-local-3d-generation`
**Phase**: Foundational State, Persistence, Storage, and Security
**Environment**: macOS development host, CPython 3.12.12 provisioned by `uv`
**Scope**: T008–T019 only. No Windows, NVIDIA GPU, ComfyUI, Hunyuan3D, LAN,
router, DNS, firewall, certificate, credential, or public-network evidence is
claimed.

## Test-first evidence

The required test tasks were run before their paired modules existed and failed
during collection only with the expected missing-module errors:

- T008: `ModuleNotFoundError: No module named 'local3d.config'`
- T010: `ModuleNotFoundError: No module named 'local3d.domain'`
- T012: `ModuleNotFoundError: No module named 'local3d.persistence'`
- T014: `ModuleNotFoundError: No module named 'local3d.services'`
- T017: `ModuleNotFoundError: No module named 'local3d.api'`

## Final verification

```text
uv run --project apps/api pytest \
  apps/api/tests/unit/test_settings.py \
  apps/api/tests/unit/test_job_state.py \
  apps/api/tests/unit/test_job_repository.py \
  apps/api/tests/unit/test_storage_and_tokens.py \
  apps/api/tests/contract/test_health_and_errors.py
40 passed

uv run --project apps/api ruff check apps/api/src/local3d apps/api/tests
All checks passed!

uv run --project apps/api mypy apps/api/src/local3d
Success: no issues found in 17 source files
```

The suite covers configuration limits and loopback enforcement, all allowed and
forbidden state transitions, terminal immutability, atomic SQLite acceptance,
foreign keys, event ordering, expiry, restart reads, busy timeout, WAL fallback,
path traversal, symlink escape, atomic writes, per-job directories, token digest
comparison, safe errors, and sensitive-log filtering.

## Local health runtime evidence

```text
uv run --project apps/api uvicorn local3d.main:app --host 127.0.0.1 --port 8000
Uvicorn running on http://127.0.0.1:8000

curl --fail --silent --show-error http://127.0.0.1:8000/api/v1/health/live
{"status":"ok"}

curl --fail --silent --show-error http://127.0.0.1:8000/api/v1/health/ready
{"status":"ok"}
```

The server was stopped after the local checks. It bound only to loopback.

## Phase verdict

`PASS` — T008–T019 verification conditions passed. The next incomplete task is
T020, the first User Story 1 contract-test task. This phase does not unlock any
hardware or public-deployment gate.
