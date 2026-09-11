# Feature 005 cloudflared service installation

- Captured (UTC): `2026-09-09T20:42:34Z`
- Gate: T082
- Host role: Production AI Notebook
- Public hostname: `mango74-api.mangosgo.com`
- Tunnel: existing remotely managed named Tunnel (identifier omitted here)

## Secure installation

The authenticated Cloudflare dashboard supplied the existing Tunnel connector
command. It was passed directly from the local clipboard to the elevated
installer with strict command-shape validation. The credential was not printed,
written to the repository, or copied into evidence. The clipboard was cleared
immediately after the installer returned exit code `0`.

## Verification

| Check | Result |
|---|---|
| Windows service exists | PASS |
| Service status | Running |
| Startup type | Automatic |
| `cloudflared` process | Running |
| Cloudflare dashboard connector status | Healthy |
| Quick Tunnel used | No |
| Credential recorded | No |

Result: **PASS — the named Tunnel connector is installed, starts automatically,
and is healthy in Cloudflare.** Public DNS and stable-API reachability are
separate T042/T083 gates and are not inferred from connector health.
