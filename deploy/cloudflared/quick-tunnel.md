# Quick Tunnel operator runbook

Use this runbook for the approved development/test exposure of the single-node AI service.

## Current-session URL and Error 1033

Every Quick Tunnel launch creates a new random `trycloudflare.com` URL. Only
the URL printed as `TEMPORARY NON-PRODUCTION URL` by the current launcher is
valid for that session. A bookmarked or shared URL from an earlier session can
show Cloudflare Error 1033 after its connector stops; do not retry or reuse the
old hostname. Start a new session and share its newly printed URL instead.

The launcher clears only its transient operator logs under
`%ProgramData%\Local3D` before launch so an expired URL is not confused with
the current one. It does not write the URL to the repository.

## Start

From the project root, after Caddy is listening on `127.0.0.1:8080`, run:

```powershell
cloudflared tunnel --url http://127.0.0.1:8080 --loglevel info
```

Copy the `https://<random>.trycloudflare.com` URL printed by `cloudflared` and provide it to the tester. The URL is temporary, public, and not an authentication mechanism. Do not put it in source control, logs, screenshots, or automated configuration.

## Stop and verify

Stop the foreground process with `Ctrl+C`. Confirm that the URL no longer responds, then verify the local path directly:

If the Tunnel was started from an Administrator PowerShell and a normal shell
cannot stop it, request elevation explicitly:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File scripts/windows/stop_quick_tunnel.ps1 -Elevate
```

```powershell
Invoke-WebRequest http://127.0.0.1:8080/healthz
Invoke-WebRequest http://127.0.0.1:8080/api/v1/health
```

The machine does not need inbound Internet access. `cloudflared` establishes outbound connectivity to Cloudflare, normally over TCP/UDP 7844; ports 3000, 8000, 8080, and 8188 remain local-only.

## Limitations

- Quick Tunnel is for non-production testing only and has a documented concurrency limit of about 200 in-flight requests.
- Do not depend on Server-Sent Events or another long-lived progress stream through this endpoint; the UI uses bounded polling of the status API.
- Do not configure a named tunnel, credentials file, DNS record, custom hostname, or automatic service from this runbook.
- A stable custom hostname is a separate, approval-gated migration after the parent domain is authorized.
