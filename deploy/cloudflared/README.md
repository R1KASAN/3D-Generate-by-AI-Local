# cloudflared — Single-Node Test Connector

Feature 004 uses an operator-started Cloudflare Quick Tunnel for development
and testing only. The Notebook runs the connector and Caddy; there is no edge
server, named tunnel, credentials file, custom hostname, DNS change, or
automatic cloudflared service in this feature.

## Approved test command

```powershell
cloudflared tunnel --url http://127.0.0.1:8080 --loglevel info
```

The generated `https://<random>.trycloudflare.com` address is temporary,
potentially public, and not authentication. It may change after every restart.
Quick Tunnel is non-production, has no SLA, allows at most 200 concurrent
in-flight requests, and does not support SSE. The frontend therefore uses
bounded HTTP polling.

## Preflight and network boundary

Before starting, review (do not rename automatically) both possible default
configuration paths under `%USERPROFILE%\.cloudflared`:

```text
config.yaml
config.yml
```

An existing operator-owned config may activate named-tunnel behavior and must be
handled explicitly before the test session. The connector requires outbound
TCP/UDP 7844; it does not require inbound application access to ports 3000,
8000, 8080, or 8188. Caddy is the only origin and is bound to
`127.0.0.1:8080`.

## What belongs in this directory

| File | Status | Purpose |
|---|---|---|
| `quick-tunnel.md` | Active | Session startup, limitations, redaction, and stop procedure |
| `config.yml.example` | Historical only | Feature-003 named-tunnel reference; never use for feature 004 |
| `services/README.md` | Historical note | Explains why no automatic cloudflared service is installed |

Do not commit a rendered cloudflared config, credentials, token, temporary URL,
or operator session output. Do not run `cloudflared tunnel login`,
`cloudflared tunnel create`, or a DNS route as part of this feature.

## Future production hostname

A stable hostname requires explicit authorization for the parent domain, a new
access policy/threat review, secret storage, DNS/Tunnel design, rollback plan,
and new end-to-end evidence. That work is outside this feature.
