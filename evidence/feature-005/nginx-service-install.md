# Feature 005 Nginx Service Installation Evidence

- Date/time (UTC): 2026-09-09
- Scope: elevated WinSW installation and local loopback verification.
- Binary hash validation: PASS; the installer accepted the operator-supplied
  SHA-256 values for WinSW and Nginx. Hash values are intentionally omitted.
- Nginx configuration validation: PASS (`nginx -t`, syntax ok and test successful).
- Service installation: PASS (`Local3D-Nginx` installed and started).
- Legacy rollback artifact: `Local3D-Caddy` retained and stopped/disabled.

Observed service state:

```text
Running  Local3D-API
Running  Local3D-ComfyUI
Running  Local3D-Nginx
Stopped  Local3D-Caddy
```

Observed listener and health:

```text
LocalAddress: 127.0.0.1
LocalPort: 8080
State: Listen
GET http://127.0.0.1:8080/api/v1/health/live
HTTP 200 {"status":"ok"}
Server: nginx
```

No direct public listener was opened by this validation.

