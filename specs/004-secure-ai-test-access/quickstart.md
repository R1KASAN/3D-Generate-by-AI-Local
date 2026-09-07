# Quickstart Validation: Secure Public Test Access on One Notebook

This is the runnable validation guide for feature 004 after implementation. It
does not install a named Tunnel, buy a domain, create DNS, or open an inbound
port. Run commands from the repository root in PowerShell unless stated
otherwise.

The temporary URL is public and changes between Quick Tunnel sessions. Keep it
out of Git, screenshots intended for permanent evidence, project logs, issue
text, and committed configuration. Per-job `X-Job-Token`, not URL obscurity,
protects job data.

## 1. Prerequisites

- Windows Notebook/PC with the project checkout.
- Python 3.12, `uv`, Node.js 24, npm 11, Caddy 2.10 or newer, and a recent
  `cloudflared`.
- Installed and verified ComfyUI/Hunyuan workflow assets for real-GPU checks.
- NVIDIA RTX 5070 driver/runtime matching the pinned workflow manifest.
- Outbound TCP and UDP 7844 allowed. No inbound application-port rule.
- A current desktop browser. An external network such as mobile data is needed
  for final public-boundary validation.
- Explicit network authorization before probing `161.200.90.4` from outside.

Check the local tools:

```powershell
uv --version
node --version
npm --version
caddy version
cloudflared version
nvidia-smi
```

Expected project versions are summarized in [plan.md](./plan.md). A mismatch in
the pinned ComfyUI/PyTorch/CUDA/workflow lane blocks real-generation evidence;
it must not be hidden by switching to mock mode.

## 2. Prepare dependencies

```powershell
uv sync --project apps/api --group dev
npm --prefix apps/web ci
```

Before modifying any Next.js source, read the relevant local guide under
`apps/web/node_modules/next/dist/docs/` as required by `apps/web/AGENTS.md`.

Runtime configuration must keep these exact bindings:

```text
Next.js   127.0.0.1:3000
FastAPI   127.0.0.1:8000
Caddy     127.0.0.1:8080
ComfyUI   127.0.0.1:8188
```

The Quick Tunnel requires no token or committed config. Do not populate the
feature-003 named-tunnel example for this validation.

## 3. Run automated gates

```powershell
Push-Location apps/api
uv run pytest
uv run ruff check .
uv run mypy src
Pop-Location

npm --prefix apps/web run test
npm --prefix apps/web run typecheck
npm --prefix apps/web run lint
npm --prefix apps/web run build
npm --prefix apps/web run test:e2e

uv run --project apps/api python scripts/verify/validate_contracts.py `
  specs/004-secure-ai-test-access/contracts/openapi.yaml `
  workflows/hunyuan3d/workflow-manifest.json
uv run --project apps/api python scripts/verify/verify_comfy_manifest.py `
  workflows/hunyuan3d/workflow-manifest.json `
  --comfy-root "$env:USERPROFILE\ComfyUI" `
  --base-url http://127.0.0.1:8188
caddy fmt --diff deploy/caddy/Caddyfile
caddy validate --config deploy/caddy/Caddyfile --adapter caddyfile

uv run --project apps/api python -c "from pathlib import Path; import yaml; yaml.safe_load(Path('specs/004-secure-ai-test-access/contracts/openapi.yaml').read_text(encoding='utf-8')); print('OpenAPI YAML: OK')"
```

Expected:

- All tests and static checks pass.
- Feature-004 tests assert Caddy 8080, one Notebook, loopback listeners,
  direct Caddy API routing, public `running`, Quick Tunnel session behavior,
  and no WireGuard/named-Tunnel dependency.
- Caddy formatting reports no diff and validation succeeds.
- Hardware-dependent tests may be explicitly separated from mock automation,
  but they need target-environment evidence before feature acceptance.

Do not accept old feature-003 Caddy/security tests unchanged: assertions for
port 8443, a second host, WireGuard, token-based named Tunnel, or custom DNS
certify the wrong architecture.

## 4. Start and verify the local chain

If the WinSW services are installed, start in dependency order from an elevated
PowerShell session:

```powershell
Start-Service -Name 'Local3D-ComfyUI'
Start-Service -Name 'Local3D-API'
Start-Service -Name 'Local3D-Web'
Start-Service -Name 'Local3D-Caddy'

Get-Service -Name 'Local3D-ComfyUI','Local3D-API','Local3D-Web','Local3D-Caddy'
```

Expected: all four show `Running`. Quick Tunnel is not an automatic WinSW
service. When developing without installed services, run the same four
components in separate terminals using the repository's loopback startup
scripts and `caddy run --config deploy/caddy/Caddyfile --adapter caddyfile`.

Verify API and routing:

```powershell
curl.exe -fsS http://127.0.0.1:8000/api/v1/health/live
curl.exe -fsS http://127.0.0.1:8000/api/v1/health/ready
curl.exe -fsS http://127.0.0.1:8000/api/v1/health/engine

curl.exe -fsS http://127.0.0.1:8080/
curl.exe -fsS http://127.0.0.1:8080/api/v1/health/live
curl.exe -fsS -H "Host: sample.trycloudflare.com" http://127.0.0.1:8080/api/v1/health/live
```

Expected: health bodies contain only safe status, the page contains the
temporary non-production notice, and the request with a public-style Host also
succeeds. `/api/v1/health/live` must arrive at FastAPI with the prefix intact.

Inspect listeners:

```powershell
$RequiredPorts = 3000, 8000, 8080, 8188
Get-NetTCPConnection -State Listen |
  Where-Object { $_.LocalPort -in $RequiredPorts } |
  Sort-Object LocalPort |
  Format-Table LocalAddress, LocalPort, OwningProcess
```

Expected: each required port appears only on `127.0.0.1`. A listener on
`0.0.0.0`, `::`, `161.200.90.4`, or another interface is a blocking failure.
Also inspect and retire any legacy Windows portproxy mapping before collecting
feature-004 target evidence; the public path must not depend on it.

Run the implemented feature-004 local health report and verify H2-H9 from
[operator-health.md](./contracts/operator-health.md). The report must identify
web, API, storage, workflow, ComfyUI, and GPU separately.

## 5. Start one Quick Tunnel test session

Cloudflare warns that Quick Tunnel is incompatible with a default local Tunnel
configuration. Detect both Windows filename variants and stop for operator
review; do not rename or delete them automatically:

```powershell
$DefaultCloudflareDir = Join-Path $env:USERPROFILE '.cloudflared'
$ConflictingConfigs = @(
  (Join-Path $DefaultCloudflareDir 'config.yaml'),
  (Join-Path $DefaultCloudflareDir 'config.yml')
) | Where-Object { Test-Path -LiteralPath $_ }

if ($ConflictingConfigs.Count -gt 0) {
  throw "Quick Tunnel preflight blocked: review the existing default cloudflared configuration."
}
```

In a dedicated terminal, start the connector without output redirection:

```powershell
cloudflared tunnel --url http://127.0.0.1:8080 --loglevel info
```

Expected: cloudflared prints a newly assigned HTTPS URL under
`trycloudflare.com`. Label it `TEMPORARY NON-PRODUCTION TEST URL` when sharing
it with the approved evaluators. Do not paste it into a repository file.

Quick Tunnel limitations relevant to this test:

- the URL can change after restart;
- there is no production SLA;
- at most 200 concurrent in-flight requests are supported;
- SSE is unsupported;
- an edge capacity response such as `429` may not contain the API's JSON shape.

The frontend therefore uses ordinary job-status polling with 2/5/10-second
backoff and a safe fallback for non-JSON errors.

## 6. Validate through the temporary HTTPS route

In the same uncommitted PowerShell session, set the current URL manually:

```powershell
$TestUrl = 'https://replace-with-current-random-host.trycloudflare.com'
$TestHost = ([Uri]$TestUrl).Host

curl.exe -fsS "$TestUrl/"
curl.exe -fsS "$TestUrl/api/v1/health/live"
```

Expected: the public page is usable, visibly says temporary/non-production,
and the API response contains only safe health status.

From an external network, run the real full journey with a valid non-sensitive
test image. Use the feature-004-revised verifier and a temporary evidence path
so the random hostname is not committed:

```powershell
$TemporaryEvidence = Join-Path $env:TEMP 'local3d-feature004-public-flow.md'
python scripts/verify/test_external_acceptance.py `
  --hostname $TestHost `
  --image C:\path\to\approved-test-image.png `
  --confirm-off-campus `
  --max-wait-seconds 1800 `
  --evidence $TemporaryEvidence
```

Expected:

1. `POST /api/v1/jobs` returns `201`, an opaque Job ID, and one Job Token within
   three seconds after upload transfer.
2. Polling shows only `queued`, `running`, `completed`, `failed`, or
   `cancelled`; refresh recovers the same authorized durable job within ten
   seconds.
3. Success produces one previewable and downloadable textured GLB, with equal
   integrity evidence and no partial result.
4. Wrong, missing, expired, and cross-job tokens all produce the same `404` and
   reveal no job data.
5. A five-user run has at most one `running` job; other accepted jobs remain
   isolated and queued.

Before retaining any evidence, replace the temporary hostname with
`<temporary>.trycloudflare.com` and verify that no Job Token, user content,
generated bytes, private path, or engine ID remains.

## 7. Exercise public failure and recovery cases

Run the approved test fixtures for corrupt/disguised input, more than 10 MiB,
path-unsafe filename, queue/rate exhaustion, low disk, unavailable adapter,
ComfyUI timeout, cancellation, missing/invalid output, and a non-JSON proxy/edge
error.

Expected status behavior follows [openapi.yaml](./contracts/openapi.yaml):

- invalid input: `413`, `415`, or `422` before AI work;
- admission pressure: `429` with retry guidance where the response is from the
  application;
- AI/job service unavailable: safe `503` while the frontend remains usable;
- low disk: `507` for new jobs, without corrupting accepted jobs;
- result absent or not safely finalized: `409`, with zero partial bytes;
- inaccessible job/token cases: uniform `404`.

While one job is queued and another is running, perform the controlled restart
matrix three times. After network readiness, local health must become accurate
within five minutes. Never-submitted queued work rehydrates; uncertain running
work fails with `restart_recovery` unless exact tested reattachment succeeds;
no job disappears, duplicates, or becomes falsely completed.

Stop and restart only cloudflared three times. Each new URL must reach the same
local data without migration. The old URL is not promised to work.

## 8. Verify no direct exposure and no log leakage

From the Notebook, retain the loopback listener inventory from section 4. From
an explicitly authorized external network, corroborate it:

```powershell
$AssignedNotebookAddress = '161.200.90.4'
3000, 8000, 8080, 8188 | ForEach-Object {
  [pscustomobject]@{
    Port = $_
    TcpConnected = Test-NetConnection `
      -ComputerName $AssignedNotebookAddress `
      -Port $_ `
      -InformationLevel Quiet `
      -WarningAction SilentlyContinue
  }
}
```

Expected: no probe obtains a project application response. A timeout/drop is
not proof by itself; pair it with local listener and firewall/routing evidence.
Do not request an inbound exception merely to make this test easier.

Send a known synthetic header through Caddy, then scan project-controlled logs:

```powershell
$RedactionSentinel = 'FEATURE004-DO-NOT-LOG-7f94d79e'
curl.exe -sS `
  -H "X-Job-Token: $RedactionSentinel" `
  http://127.0.0.1:8080/api/v1/health/live | Out-Null

rg -n --fixed-strings $RedactionSentinel deploy/windows/services logs evidence
```

Expected: zero matches. Repeat the repository/log scan with controlled test
values for authorization, cookies, user filename/content, and generated output.
Sanitized evidence may contain safe Job IDs and request IDs only.

## 9. Stop the session safely

In the Quick Tunnel terminal, press `Ctrl+C` and confirm public access stops
while these local checks continue to work:

```powershell
curl.exe -fsS http://127.0.0.1:8080/
curl.exe -fsS http://127.0.0.1:8080/api/v1/health/live
```

For a complete controlled shutdown, stop the remaining layers in order from an
elevated PowerShell session:

```powershell
Stop-Service -Name 'Local3D-Caddy'
Stop-Service -Name 'Local3D-Web'
Stop-Service -Name 'Local3D-API'
Stop-Service -Name 'Local3D-ComfyUI'
```

Expected: no temporary public route remains, application data is not migrated
or deleted, and the next startup performs documented reconciliation.

## Future custom-hostname migration (not authorized now)

Do not execute a hostname migration under this feature. After explicit written
authorization to use a parent domain, create a new/updated specification and
plan covering domain ownership, Cloudflare zone permissions, named-Tunnel
credentials, DNS, access policy, production threat assessment, secret storage,
availability expectations, rollback, and new end-to-end evidence. Authorization
to run this Quick Tunnel test is not authorization for any of those changes.
