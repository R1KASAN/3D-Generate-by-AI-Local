# Phase 3 Evidence — Local 3D Generation MVP

**Phase:** 3 — User Story 1, macOS mock upload/preview/download  
**Feature:** `001-local-3d-generation`  
**Environment:** macOS, CPython 3.12.12, Node/Vitest, deterministic mock adapter  
**Scope boundary:** T020–T034 only. No Windows, NVIDIA GPU, ComfyUI, Hunyuan3D,
LAN, router, DNS, certificate, firewall, or public-network evidence was used.

## Test-first evidence

The contract and unit tests were first run before their implementation modules
existed and failed at the expected missing-route/module boundaries:

- T020: job route contract failed because the routes were not implemented.
- T021: upload validation failed with missing `image_validation.py`.
- T022: adapter contract failed with missing `local3d.adapters`.
- T023: GLB publication tests failed with missing `glb_publication.py`.
- T024: viewer test failed at the missing viewer component after the Vitest JSX
  configuration was corrected.
- T025: generation-flow test failed at missing API/UI modules.

## Verification commands

All Phase 3 required checks passed:

```text
uv run --project apps/api pytest apps/api/tests/contract/test_jobs_api.py
3 passed

uv run --project apps/api pytest apps/api/tests/unit/test_upload_validation.py
8 passed

GENERATION_ADAPTER=mock uv run --project apps/api pytest apps/api/tests/contract/test_generation_adapter.py
2 passed

uv run --project apps/api pytest apps/api/tests/unit/test_glb_publication.py
3 passed

npm --prefix apps/web run test
2 test files passed, 5 tests passed

uv run --project apps/api ruff check apps/api/src/local3d apps/api/tests
All checks passed

uv run --project apps/api mypy apps/api/src/local3d
Passed (no diagnostics)

uv run pytest  # executed from apps/api so its pyproject test configuration applies
56 passed
```

Frontend type checking also passed:

```text
npm --prefix apps/web run typecheck
Passed (tsc --noEmit)
```

Vitest emitted only a non-failing Vite `configLoader: 'native'` warning about
the current CommonJS/ESM configuration. Frontend lint was not required for
T020–T034 and remains a later Phase 6 check; invoking it currently reports the
repository's missing ESLint 9 flat configuration.

## Manual mock-flow evidence

See [`evidence/mock/us1-manual.md`](../mock/us1-manual.md) for the exact
TestClient command and output. The observed state sequence was:

```text
queued → processing → completed
```

The preview and download endpoints both returned HTTP 200 and the bytes were
identical:

```text
model_sha256    = 5039d930f833b34e65ded1117e0d94a897eef954e87c2b2a3ea21426e53bb916
download_sha256 = 5039d930f833b34e65ded1117e0d94a897eef954e87c2b2a3ea21426e53bb916
bytes           = 1236
```

## Phase verdict

`PASS` for T020–T034. The local mock vertical slice is independently testable:
validated JPEG/PNG upload → opaque job/token → persisted job/status → mock
textured GLB publication → browser viewer component → byte-identical preview
and download.

The next incomplete implementation task is T035 (Phase 4). This phase did not
reach or claim the Windows NVIDIA/ComfyUI/Hunyuan3D hardware gate.
