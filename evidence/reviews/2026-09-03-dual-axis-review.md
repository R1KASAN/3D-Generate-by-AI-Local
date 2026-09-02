# Dual-axis implementation review

Date: 2026-09-03

## Comparison boundary

The repository has no `HEAD` commit and every project artifact is currently
untracked. A commit diff or commit-list review was therefore impossible. This
review used a read-only snapshot inventory as the fixed fallback comparison
point and did not stage, commit, or rewrite user files merely to manufacture a
baseline.

## Standards axis

Confirmed hard findings:

1. The unanchored `storage/` ignore rule hid the required
   `apps/api/src/local3d/storage` source package.
2. `JobService` was coupled to the mock class and silently selected mock even
   when `GENERATION_ADAPTER=comfyui` was configured.
3. Restart reconciliation stranded durable queued jobs.
4. Expired model/download routes returned a distinguishable 410 response.
5. Job state, output asset, and event changes committed independently.

One non-blocking P3 duplication smell remains in the frontend polling hook. It
was not changed because it does not violate the governing MVP behavior and the
request limited implementation to required conformance fixes.

## Specification axis

Confirmed findings:

1. T015 could not survive a clean checkout because its source package was
   ignored.
2. Viewer buttons did not control `OrbitControls` or reset the camera.
3. T039 did not restore queued jobs or revalidate completed outputs.
4. FR-018 had no automatic 24-hour file cleanup.
5. T049 did not provide uniform not-found behavior for expired results.
6. T050 used only a process-local guard and did not durably reserve submission.

## Implemented corrections

- Anchored runtime storage ignore to `/storage/` and verified the source package
  is no longer ignored.
- Added a stable `GenerationAdapter` protocol and fail-closed behavior for the
  not-yet-implemented real adapter. No Windows/ComfyUI evidence was claimed.
- Added durable queued-job rehydration, fail-safe recovery of uncertain attempts,
  completed-output revalidation, and a safe `output_missing` operator event.
- Added startup and periodic retention cleanup that removes only expired terminal
  job trees and then their database rows.
- Added one SQLite transaction for optional output asset + job transition +
  event, with rollback proof.
- Added an atomic SQLite submission reservation so automatic submission is
  single-use across process restarts.
- Made expired status/preview/download responses uniformly 404.
- Connected rotate/zoom/pan modes to `OrbitControls` and made reset call the
  actual controls instance.
- Corrected stale owner-decision checklist text and documented the owner-approved
  macOS-before-hardware dependency exception.

## Verification evidence

```text
uv run --project apps/api pytest
102 passed

uv run --project apps/api ruff check apps/api/src apps/api/tests
All checks passed!

uv run --project apps/api mypy apps/api/src apps/api/tests
Success: no issues found in 51 source files

npm --prefix apps/web run test
8 passed

npm --prefix apps/web run typecheck
PASS

npm --prefix apps/web run lint
PASS

npm --prefix apps/web run build
PASS

npm --prefix apps/web run test:e2e
4 passed
```

Static OpenAPI/workflow-manifest validation, fixture-manifest verification, and
the textured sample GLB validator also passed. The ESM-config Vite warning is
retained because the one-line package-mode change broke existing Playwright
`__dirname` usage; broad config migration was not required for MVP conformance.

## Gate status

The reviewed macOS/mock slice conforms after these corrections. T058 is still
the first incomplete task and remains blocked on real Windows NVIDIA server
evidence. No Windows, GPU, LAN, router, DNS, certificate, or public-network
claim was made by this review.
