# Feature 005 Foundation Validation

Captured: 2026-09-09 (local validation)

Targeted command:

```powershell
uv run --project apps/api python -m pytest apps/api/tests/unit/test_settings.py apps/api/tests/security/test_cors_policy.py apps/api/tests/contract/test_feature005_openapi.py tests/security/test_feature005_architecture_contract.py tests/security/test_nginx_contract.py tests/security/test_feature005_services_contract.py tests/security/test_frontend_package_contract.py -q
```

Result: PASS — targeted contract/security tests passed. The full regression
later reached 286 passed and 7 skipped.

Frontend commands:

```powershell
npm run test --prefix apps/web
npm run typecheck --prefix apps/web
npm run lint --prefix apps/web
```

Result: PASS — 7 test files / 29 tests passed; TypeScript typecheck passed;
ESLint passed. Vitest printed a non-failing Vite config-loader warning.

Static build/package command:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows\build_frontend_package.ps1 -ProjectRoot (Get-Location).Path -OutputPath .\tmp\front-end.zip -PythonPath python
```

Result: PASS — static export, tree validation, archive validation, and SHA-256
manifest generation passed for production and preview modes. The optional
Nginx `-t` step was not run because no operator-verified Nginx binary was
available; WinSW runtime installation remains a later service/manual gate.
