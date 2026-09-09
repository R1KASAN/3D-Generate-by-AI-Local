# Mango74 production runbook

## Preflight

1. Confirm the approved stable API hostname and the NT frontend release hash.
2. Build `front-end.zip` with `scripts/windows/build_frontend_package.ps1` and scan it before handoff.
3. Confirm ComfyUI, API, GPU, storage, and workflow readiness locally.
4. Ensure no unsafe active job is running before proxy or Tunnel changes.

## Cutover

1. Stop/disable `Local3D-Caddy` but retain its definition for rollback.
2. Validate the operator-supplied Nginx hash and run `nginx.exe -t`.
3. Install/start `Local3D-Nginx`; verify `Host: mango74-api.mangosgo.com` and `/api/v1/health/live` on loopback.
4. Ask the authorized Cloudflare administrator to activate the named Tunnel to `http://127.0.0.1:8080`.
5. Deploy only the compiled archive under `/mango74/` on the NT Server, then open the route with `mango74-vhost.py` following `docs/runbooks/mango74-vhost-activation.md`. `www.mangosgo.com` has duplicate server blocks, so the include must go in the block Nginx actually uses, not in `sites-available/default`.
6. Run the Feature 005 health chain and the guarded external verifier from an independent network.

## Diagnosis and restart

Use `scripts/windows/verify_services.ps1 -Feature005` and `scripts/windows/health_chain.ps1 -Feature005`.
Restart only one dependency at a time, wait for readiness, and verify durable job state before continuing.
Never expose ports 3000, 8000, 8080, or 8188 directly.

## Escalation

Stop when the stable hostname, Cloudflare route, NT Server route, or rollback identifier is unknown. Do not record tokens, credentials, private URLs, user files, model bytes, or raw internal addresses in evidence.
