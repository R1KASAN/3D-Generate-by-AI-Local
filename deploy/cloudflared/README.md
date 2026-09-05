# cloudflared — Approved Origin Connector

**Feature**: `003-outbound-tunnel-entry`

This directory holds the **outbound** Cloudflare Tunnel connector configuration for the approved origin. It replaces feature 002's inbound origin proxy: the origin has no public listener, no Origin CA certificate, and no Authenticated Origin Pulls trust store. See [contracts/origin-entry.md](../../specs/003-outbound-tunnel-entry/contracts/origin-entry.md).

## What lives here

| File | Committed? | Contents |
|---|---|---|
| `config.yml.example` | Yes | Template with placeholder values only |
| `config.yml` | **No — gitignored** | Rendered config with the real tunnel ID and hostname |
| `<tunnel-id>.json` | **No — gitignored** | Credentials file `cloudflared tunnel create` writes |
| `services/` | Partially | Provisional per-OS service-unit definitions (origin OS is unverified — see `specs/003-outbound-tunnel-entry/research.md` R1) |

## Credential storage (FR-032)

- The credentials JSON is the tunnel's private key material. It MUST live **outside Git**, exactly where `cloudflared tunnel create` writes it (do not copy it into this repository checkout).
- File permissions MUST be least-privilege: readable only by the account running the `cloudflared` service, not world- or group-readable.
- `config.yml` (the rendered version, not the `.example` template) MUST also stay outside Git, because it references the credentials path and the production hostname.

## Setup (operator-executed, on the approved origin)

1. `cloudflared tunnel login` — authenticates this host to the project's Cloudflare account.
2. `cloudflared tunnel create <name>` — creates the tunnel and writes the credentials JSON. Record its path; do not move it into this repo.
3. Copy `config.yml.example` to a location outside Git (e.g. the same directory as the credentials file) as `config.yml`, and fill in `TUNNEL_ID`, `TUNNEL_CREDENTIALS`, and `PUBLIC_HOSTNAME`.
4. Route DNS for the production hostname to the tunnel, inside the Cloudflare account that manages the hostname's zone (see FR-011a — for `twin3dgen.mangosgo.com` this is the account managing `mangosgo.com`, not a project-owned account).
5. Install the connector as an OS service using the unit definition in `services/` appropriate to the origin's actual OS (see that directory's README for why this step is still provisional).

## Revocation and replacement (FR-032, SC-013)

1. Revoke the compromised or rotated credential from the Cloudflare dashboard or `cloudflared tunnel delete-credential`.
2. Confirm the connector using that credential stops carrying traffic — the tunnel should show as down in the dashboard, and origin-side health should report the connector layer unhealthy (see `contracts/health-chain.md`).
3. Create a new tunnel or a new credential for the same tunnel and update `config.yml`'s `TUNNEL_CREDENTIALS` path.
4. Restart the `cloudflared` service. The **same public hostname** MUST come back without any inbound service being exposed at any point in this procedure.
5. Record the rotation in the project's operational log per FR-027 (no credential material in the log — only that a rotation occurred and when).

## What is deliberately absent

No `Caddyfile`, no TLS certificate, and no client-CA trust store belong in this directory. Those concerns live in `deploy/caddy/` and, under the outbound design, the origin holds none of the certificate material feature 002 required — see `contracts/origin-entry.md` O2 for the full list of what was removed and why.
