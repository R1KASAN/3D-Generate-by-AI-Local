# Quickstart validation snapshot

Executed locally:

- API/security/contract pytest suites: PASS (see regression evidence).
- Frontend unit/typecheck/lint: PASS.
- Isolated Playwright mock flows: PASS; no real GPU work.
- Static frontend production and preview package builds: PASS.
- PowerShell parser and XML contract checks: PASS.
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/windows/health_chain.ps1 -Feature005 -Json` executed. It correctly reported API/ComfyUI/GPU/storage/workflow/listener checks as healthy while reporting Nginx, named Tunnel, and stable public API as unavailable because those production services are not installed/configured in this environment.
- Nginx runtime `-t`, named Tunnel, NT Server deployment, independent-network acceptance, and Firebase administrator deployment: NOT RUN because the operator-controlled binaries/credentials/hosts were not supplied.
