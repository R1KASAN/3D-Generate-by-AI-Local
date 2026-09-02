# Phase 6 Gate — First Shippable macOS Mock Slice

**Feature:** `001-local-3d-generation`  
**Environment:** macOS, CPython 3.12.12, Node.js/Next.js, Playwright Chromium,
SQLite, deterministic mock adapter  
**Scope:** T053–T057 only. The E2E server binds FastAPI to `127.0.0.1:8000`
and Next.js to a local test port; no ComfyUI, Hunyuan3D, NVIDIA, LAN, router,
DNS, certificate, firewall, or Internet evidence is claimed.

## Verification commands and results

Backend (run from `apps/api` so its `pyproject.toml` test configuration applies):

```text
uv run --project apps/api pytest
77 passed

uv run --project apps/api ruff check .
All checks passed!

uv run --project apps/api mypy apps/api/src
Success: no issues found in 29 source files
```

Frontend:

```text
npm --prefix apps/web run test
3 test files passed, 8 tests passed

npm --prefix apps/web run typecheck
Passed (tsc --noEmit)

npm --prefix apps/web run lint
Passed (ESLint 9 flat config)

npm --prefix apps/web run build
Compiled successfully; static routes `/` and `/_not-found` generated
```

Browser gate:

```text
GENERATION_ADAPTER=mock npm --prefix apps/web run test:e2e
4 passed (7.1s), Playwright configured with workers=1
```

The four browser checks cover upload → queued/progress → completed → GLB
viewer/download, refresh/reconnect using the same session token, safe failure
messaging, and two-job distinct-token/swapped-access isolation. The happy path
observed the viewer canvas and captured a `.glb` download. E2E browser requests
use the Next.js same-origin rewrite and never call port 8188 directly.

The Playwright Chromium binary was installed in the developer machine's local
browser cache to make this verification runnable; it is not a production
runtime or an external deployment change.

## Phase verdict

`PASS` — the first independently shippable macOS/mock artifact is verified:
browser upload → serial mock queue/progress → textured sample GLB preview with
controls → download, with recovery and cross-job checks.

The next task is T058, the Windows NVIDIA runtime inventory. No hardware gate
work was started in this phase. Per project instruction, stop here and obtain
real Windows + NVIDIA + ComfyUI/Hunyuan3D evidence before proceeding.
