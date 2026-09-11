# Feature 005 Cloudflare activation

- Captured (UTC): `2026-09-09T20:42:34Z`
- Administrator: authenticated Cloudflare Super Administrator (identity
  redacted)
- Named Tunnel: existing remotely managed `cloudflared` Tunnel
- Approved route: `mango74-api.mangosgo.com` to
  `http://127.0.0.1:8080`
- Catch-all: `http_status:404`

## Actions and observed state

1. Preserved the Tunnel's unrelated pre-existing application route.
2. Added the exact Mango74 API hostname with no path restriction and the
   approved loopback Nginx HTTP origin.
3. Cloudflare displayed `Successfully saved settings` and the route list shows
   the exact hostname and origin.
4. Installed the connector as the automatic Windows `cloudflared` service.
5. Cloudflare reports the Tunnel connector as `Healthy`.

## Remaining DNS gate

The authenticated account owns a different Cloudflare zone and does not own
`mangosgo.com`. The authoritative zone uses Cloudflare nameservers, but public
queries through both Cloudflare and Google resolvers return no record for
`mango74-api.mangosgo.com`. Therefore the public route is not yet reachable.

Result: **BLOCKED — Tunnel ingress and connector activation succeeded, but T042
remains open until an administrator of the Cloudflare account that owns
`mangosgo.com` creates the proxied Tunnel DNS record (or grants access to do
so), and public DNS plus HTTPS/CORS verification passes.** No direct-IP or
Quick-Tunnel fallback was added.
