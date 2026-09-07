# Feature 004 foundation gate

Validated on 2026-09-06 from the repository root. No temporary URL,
credential, token, or model artifact is recorded here.

## Commands and results

```text
uv run --project apps/api pytest tests/security/test_caddy_contract.py tests/security/test_caddy_runtime.py tests/security/test_single_node_architecture_contract.py tests/security/test_single_node_services_contract.py apps/api/tests/unit/test_settings.py apps/api/tests/unit/test_database.py -q
26 passed in 1.68s

$env:API_UPSTREAM='http://127.0.0.1:8000'
$env:WEB_UPSTREAM='http://127.0.0.1:3000'
$env:CADDY_MAINTENANCE_ROOT=(Resolve-Path deploy/caddy/maintenance).Path
$env:CADDY_LOG_PATH=(Join-Path (Get-Location) 'output/caddy-access.log')
& .\tmp\caddy-validation\caddy.exe validate --config .\deploy\caddy\Caddyfile --adapter caddyfile
Valid configuration

npm run typecheck --prefix apps/web
PASS
```

The runtime test starts Caddy only on an ephemeral loopback port and uses two
ephemeral loopback mock upstreams. It verifies `/api/*` and frontend routing,
safe upstream failure status, and no direct Internet dependency. The Caddy
binary was supplied by the repository's existing validation fixture because
`caddy` is not installed on PATH; this remains an operator setup note, not an
architecture exception.
