# Phase 8 macOS/mock component evidence

Date: 2026-09-03

## Scope

T065–T067 and T069–T071 were implemented and verified on macOS using an
HTTPX mock transport and an injected fake WebSocket. No ComfyUI process, Windows
NVIDIA runtime, GPU, LAN, or public deployment was used.

## Test-first evidence

The initial test-only run failed during collection with exactly the expected
missing-module errors for `comfy_client`, `workflow_mapper`, and
`output_resolver`. After implementation, the same suite passed:

```text
cd apps/api
uv run --project apps/api pytest \
  tests/contract/test_comfy_client.py \
  tests/unit/test_workflow_mapping.py \
  tests/unit/test_comfy_output_discovery.py
18 passed in 0.10s
```

The tests cover `/prompt`, `/queue`, `/history`, queue membership, safe history
failure mapping, WebSocket disconnect, timeout, restart reconciliation, loopback
URL enforcement, immutable workflow hashing, allowlisted field injection,
prefix traversal, zero/one/multiple GLB discovery, stale files, symlink escape,
and invalid Job IDs.

Static checks:

```text
uv run --project apps/api ruff check .
All checks passed!

uv run --project apps/api mypy src/local3d
Success: no issues found in 32 source files
```

This evidence does not unlock T068 or any real ComfyUI/GPU task. The next gate
remains T058, which requires Windows NVIDIA server evidence.

## Constitution exception record

- **Reason**: The owner explicitly directed implementation of all safe macOS/mock
  work before stopping at the Windows NVIDIA hardware gate.
- **Risk**: Mocked HTTP/WebSocket behavior proves the adapter boundary only; it
  does not prove ComfyUI node compatibility, CUDA execution, or GLB generation.
- **Owner approval**: Recorded in the project conversation before T065–T067 and
  T069–T071 were implemented.
- **Review trigger**: Reassess these components after T058–T064 have current
  Windows NVIDIA evidence and before T068, T072, or any real-runtime claim.
