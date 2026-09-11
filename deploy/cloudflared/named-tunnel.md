# Mango74 Production Named Tunnel

Feature 005 production uses an authorized remotely managed Cloudflare Tunnel,
not the Feature 004 random Quick Tunnel. The Cloudflare administrator maps
only:

```text
mango74-api.mangosgo.com -> http://127.0.0.1:8080
```

The connector runs on the RTX 5070 AI Notebook and connects outbound to
Cloudflare. Nginx on `127.0.0.1:8080` is the only local origin. FastAPI
`127.0.0.1:8000` and ComfyUI `127.0.0.1:8188` are never published.

## Administrator handoff

1. Confirm the authorized stable hostname and preserve unrelated
   `www.mangosgo.com` routes.
2. Create/approve the named Tunnel and route only the stable API hostname to
   `http://127.0.0.1:8080`.
3. Transfer the connector token through the approved secure channel. Never put
   it in the repository, command transcript, evidence, or a frontend build.
4. Install/start the connector as a Windows service on the Production AI
   Notebook and record only service state, hostname, route ID, and redacted
   health output.
5. Keep the rollback action ready: stop/disable the connector and restore the
   previous authorized route without adding a direct-IP fallback.

The stable URL must remain unchanged after connector restarts. A
`trycloudflare.com` URL is a development test address and is not valid
production evidence.
