# Feature 005 external frontend precheck

- Captured (UTC): `2026-09-09T20:22:19Z`
- Scope: read-only public frontend and one deployed hashed asset.
- This is partial evidence for H1/T044. It does not claim that the stable API,
  named Tunnel, real production job, CORS, or authenticated GLB checks passed.

## Browser observation

An ordinary HTTPS browser load of `https://www.mangosgo.com/mango74/`
rendered the production `Local 3D Generator` page. The loaded-resource
inventory included one stylesheet and eight JavaScript chunks below
`/mango74/_next/static/`. No alternate frontend origin was used.

## Independent multi-region HTTP probes

The page and one hashed release stylesheet were submitted to a third-party
multi-region HTTP checker. The checker initiated the requests from nodes
outside both the NT Server network and the AI Notebook.

| Target | Reported nodes | HTTP 200 | Other result |
|---|---:|---:|---|
| `/mango74/` | 56 | 54 | 2 nodes returned Cloudflare 522 |
| `/mango74/_next/static/chunks/2o_dwpqs6eksx.css` | 55 | 53 | 2 nodes returned Cloudflare 522 |

Reports:

- Page: https://check-host.net/check-report/4ac40ed1kbc1
- Hashed asset: https://check-host.net/check-report/4ac41112ke80

Result: **PASS for the required independent-network page and hashed-asset
HTTP 200 observations, with a regional 522 anomaly retained for follow-up.**
T044 remains open until the named Tunnel exists and the guarded real-job,
CORS, GLB integrity, ownership, and redaction checks pass.
