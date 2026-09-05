# Cost Boundary Verification (T041)

- Date/time (UTC): 2026-09-05T20:30:12.468407+00:00
- Dependencies checked: 8
- Credentials, capability tokens, and full public IP addresses are omitted.

| Check | Observed | Expected | Verdict |
|---|---|---|---|
| cloudflared (connector software)-zero-cost | $0 | $0 recurring | **PASS** |
| cloudflared (connector software)-no-card-required | False | false | **PASS** |
| cloudflared (connector software)-no-paid-fallback | False | false | **PASS** |
| Cloudflare Tunnel (free plan)-zero-cost | $0 | $0 recurring | **PASS** |
| Cloudflare Tunnel (free plan)-no-card-required | False | false | **PASS** |
| Cloudflare Tunnel (free plan)-no-paid-fallback | False | false | **PASS** |
| twin3dgen.mangosgo.com-zero-cost | $0 | $0 recurring | **PASS** |
| twin3dgen.mangosgo.com-no-card-required | False | false | **PASS** |
| twin3dgen.mangosgo.com-no-paid-fallback | False | false | **PASS** |
| Visitor TLS certificate-zero-cost | $0 | $0 recurring | **PASS** |
| Visitor TLS certificate-no-card-required | False | false | **PASS** |
| Visitor TLS certificate-no-paid-fallback | False | false | **PASS** |
| Caddy (loopback pass-through)-zero-cost | $0 | $0 recurring | **PASS** |
| Caddy (loopback pass-through)-no-card-required | False | false | **PASS** |
| Caddy (loopback pass-through)-no-paid-fallback | False | false | **PASS** |
| WireGuard (private binding)-zero-cost | $0 | $0 recurring | **PASS** |
| WireGuard (private binding)-no-card-required | False | false | **PASS** |
| WireGuard (private binding)-no-paid-fallback | False | false | **PASS** |
| WinSW (service supervision)-zero-cost | $0 | $0 recurring | **PASS** |
| WinSW (service supervision)-no-card-required | False | false | **PASS** |
| WinSW (service supervision)-no-paid-fallback | False | false | **PASS** |
| zrok (degraded-production fallback)-zero-cost | $0 | $0 recurring | **PASS** |
| zrok (degraded-production fallback)-no-card-required | False | false | **PASS** |
| zrok (degraded-production fallback)-no-paid-fallback | False | false | **PASS** |

- Verifies evidence/public-deployment/cost-boundary.md's claims (SC-005); does not itself query any provider account.
- Overall verdict: **PASS**
