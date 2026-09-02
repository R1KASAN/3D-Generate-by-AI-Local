# Quickstart and Verification: Local 3D Generation MVP

This is a planning-time runbook. Commands become executable after implementation
creates the listed project files. Mock evidence never substitutes for Windows GPU,
LAN, reboot, or public-network evidence.

Before a Windows AI setup or ComfyUI integration task, consult the scoped source
register at [`docs/reference/ai-runtime-sources.md`](../../docs/reference/ai-runtime-sources.md).
It does not override the pinned workflow manifest or the verification gates below.

## 1. macOS mock development

Prerequisites: Node.js 24 LTS, Python 3.12, Git, and `uv`.

```bash
uv sync --project apps/api --group dev
npm --prefix apps/web ci
```

Terminal 1:

```bash
GENERATION_ADAPTER=mock uv run --project apps/api uvicorn local3d.main:app --host 127.0.0.1 --port 8000 --reload
```

Terminal 2:

```bash
npm --prefix apps/web run dev
```

Open `http://127.0.0.1:3000`, upload a supported fixture, generate, refresh during
processing, preview the textured GLB, use rotate/zoom/pan/reset, then download it.

## 2. Automated verification

```bash
uv run --project apps/api pytest
uv run --project apps/api ruff check .
uv run --project apps/api mypy src
npm --prefix apps/web run test
npm --prefix apps/web run typecheck
npm --prefix apps/web run lint
npm --prefix apps/web run build
npm --prefix apps/web run test:e2e
```

Required test evidence includes valid upload, invalid type, corrupt image,
oversized upload, two queued jobs, wrong-job token, failure, missing GLB, refresh,
preview, download, cleanup, low-disk admission, and restart reconciliation.

## 3. Windows GPU gate

Before integrating the real adapter:

```powershell
nvidia-smi
py -3.12 -c "import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0)); print(torch.cuda.get_device_properties(0).total_memory)"
py -3.12 -c "import sqlite3; print(sqlite3.sqlite_version)"
```

Then execute and retain evidence for:

1. Pinned ComfyUI and custom-node commits plus package/model/license hashes.
2. `/object_info` compatibility validation.
3. Native shape-only smoke generation.
4. API-only full shape-plus-texture generation to one GLB.
5. GLB structural report proving mesh, UV, material, and texture.
6. Two serial jobs with isolated directories and no OOM/overwrite.
7. Failure, timeout, missing output, and restart reconciliation.

Do not mark the textured-GLB gate complete from a shape-only result.

## 4. LAN gate

- Bind public-facing LAN access only through the intended reverse-proxy test path.
- Confirm full upload-to-download flow from a second LAN device.
- From that device, confirm ports 8000 and 8188 are unreachable.
- Refresh/reconnect during processing and confirm the same job returns.
- Record commands, timestamps, Job IDs, screenshots/logs, and GLB validation hash.

## 5. Windows service and reboot gate

- Run components under the restricted service identity.
- Confirm ComfyUI can use the GPU from that session; use the documented restricted
  Task Scheduler fallback only if service-session evidence fails.
- Reboot the host and verify ordered startup, queue reconciliation, health, and one
  new full generation without manually opening terminals.

## 6. Public Deployment gate

Do not begin until Windows textured GLB, full LAN flow, Caddy/firewall, minimum
access control, service/reboot, and license/territory review gates pass.

1. Owner locks the domain/DDNS name and permitted authorized-user territory.
2. Reverify the owner-declared current Public IP from the retained project
   reference, whether it is static/dynamic, whether CGNAT applies, and whether the
   router can forward 80/443. Do not commit the IP to source.
3. Configure Caddy shared credentials using a password hash, never plaintext.
4. Bind Next.js, FastAPI, and ComfyUI to loopback.
5. Allow public inbound 443; allow 80 only for redirect/certificate issuance.
6. Validate Caddy configuration before restart.
7. Test from an external network: HTTPS certificate, shared login, upload,
   progress, preview, download, wrong-job token, and expiry.
8. Scan externally and record that 3000, 8000, 8188, and 3389 are unreachable.

## Evidence record template

```text
Gate:
Date/time and operator:
Host/environment:
Pinned revisions/hashes:
Commands or manual steps:
Expected result:
Observed result:
Artifact/log/screenshot paths:
Verdict: PASS | FAIL | BLOCKED
Blocker and smallest owner action:
```
