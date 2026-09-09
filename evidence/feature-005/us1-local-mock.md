# Feature 005 US1 Local Mock Evidence

- Date/time (UTC): 2026-09-09
- Scope: isolated browser flow through test-only Nginx, without RTX/GPU work.
- Test topology: browser/frontend `127.0.0.1:3100` → Nginx `127.0.0.1:18000` → mock FastAPI `127.0.0.1:18001`.
- Production ports were not changed: FastAPI remains `127.0.0.1:8000`; production Nginx remains `127.0.0.1:8080`.

## Commands and results

```text
$env:E2E_NGINX='1'; npm run test:e2e -- --grep "cross-origin mock API supports"
1 passed

$env:E2E_NGINX='1'; npm run test:e2e
11 passed (40.1s)

$env:NGINX_BINARY=deploy\windows\services\nginx.exe
uv run --project apps/api pytest tests/security/test_nginx_runtime.py -q
2 passed in 2.44s
```

The browser flow uploaded the fixture, submitted a job, observed lifecycle
progress, reached `completed`, displayed the GLB preview, and exposed the
download action. The Playwright API-origin assertion observed only the
test-only Nginx origin. The mock adapter was used; no real ComfyUI or GPU work
was submitted.

