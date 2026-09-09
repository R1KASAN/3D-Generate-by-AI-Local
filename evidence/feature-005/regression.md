# Feature 005 regression

Validation timestamp (UTC): `2026-09-09T08:25:08Z`.

Executed commands and results during this implementation pass:

- `$env:PYTHONPATH=(Get-Location).Path; uv run --project .\apps\api pytest -q`
  — **287 passed, 7 skipped**, exit 0. Pytest emitted a Windows temporary
  directory cleanup permission warning after the passing run; no test failed.
- `uv run --project .\apps\api ruff check apps/api/src tests scripts` —
  **PASS**.
- `uv run --project .\apps\api mypy apps/api/src` — **PASS**.
- `npm test --prefix apps/web` — **29 passed** across 7 files.
- `npm run typecheck --prefix apps/web` — **PASS**.
- `npm run lint --prefix apps/web` — **PASS**.
- `npm run test:e2e --prefix apps/web` — **11 passed** through the isolated
  mock API; no GPU adapter ran.
- `E2E_NGINX=1 npm run test:e2e --prefix apps/web` — **11 passed** through
  test-only Nginx (`127.0.0.1:18000`) to API (`127.0.0.1:18001`); production
  ports were unchanged and no GPU adapter ran.
- `uv run --project .\apps\api pytest .\tests\security\test_nginx_runtime.py -q`
  with `NGINX_BINARY` set — **2 passed**.
- `nginx.exe -t -p C:\ProgramData\Local3D\nginx -c
  C:\ProgramData\Local3D\nginx\nginx.conf` — **syntax ok; test successful**.
- PowerShell parser over `scripts/**/*.ps1` — **23 files parsed successfully**.
- `build_frontend_package.ps1 -DeploymentEnv production` — **PASS**; static
  tree and archive validators returned `valid: true`.
- `build_frontend_package.ps1 -DeploymentEnv firebase-preview` — **PASS**;
  static tree and archive validators returned `valid: true`, with the preview
  tree staged under `/mango74/`.
- Feature 005 failure matrix with `NGINX_BINARY` set — **5/5 cases passed**;
  leak scans passed and sanitized evidence was written.
- `health_chain.ps1 -Feature005 -Json` — Nginx/API/storage/workflow/ComfyUI/
  GPU, listener, and process boundaries healthy; NamedTunnel and StablePublicApi
  correctly **false** because the authorized named Tunnel and stable hostname
  are not configured.
- `run_feature005_recovery_matrix.ps1` preflight — **BLOCKED** before any
  restart because the required `cloudflared` service is not installed.

The real local Nginx → FastAPI → ComfyUI → RTX 5070 result remains in
`us1-local-real.md`; it was not rerun in this pass.
