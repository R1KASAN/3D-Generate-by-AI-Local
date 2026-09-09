# Feature 005 Static Frontend Package

Captured: 2026-09-09 (local validation; Linux-portable package rebuilt after
the NT Server staging check exposed Windows ZIP separators/permissions)

Command:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows\build_frontend_package.ps1 -ProjectRoot (Get-Location).Path -OutputPath .\artifacts\front-end.zip -PythonPath C:\Users\MetaHosP\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -DeploymentEnv production
```

Result: PASS. Next 16.3.4 produced a static export; the validator passed both
the output tree and archive. The archive contains 24 static files and no
Backend/runtime/model/workflow/upload/credential or internal endpoint matches.
All raw ZIP member names use POSIX `/` separators and every file carries Unix
regular-file mode `0644` (`0100644`), preventing the Linux extraction failure
observed with the earlier PowerShell `Compress-Archive` package.

Archive SHA-256:

```text
472D988BEC81333CBC505B2C020EFC4335C02841AFE801BB22384C072E65929E
```

Build variables were cleared by the script. The deployable archive is
`artifacts/front-end.zip`; generated release artifacts remain ignored by
version control.

Targeted regression:

```text
pytest tests/security/test_frontend_package_contract.py -q
6 passed
```
