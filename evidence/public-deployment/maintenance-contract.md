# Maintenance contract evidence

**Feature:** `002-cloudflare-public-entry`  
**Task:** T037  
**Checked:** 2026-09-05  
**Scope:** Static contract verification only; live origin/laptop behavior remains an external acceptance task.

## Results

| Check | Result | Evidence |
|---|---|---|
| Maintenance page is a deliberate service notice | PASS | `deploy/caddy/maintenance/maintenance.html` explains that the compute node is offline or reconnecting, gives a retry expectation, and does not expose an error trace or internal service detail. |
| Caddy handles upstream 502 | PASS | `deploy/caddy/Caddyfile` matches status 502 in `handle_errors` and serves `maintenance.html`. |
| Caddy handles upstream 503 | PASS | `deploy/caddy/Caddyfile` matches status 503 in `handle_errors` and serves `maintenance.html`. |
| Caddy handles upstream 504 | PASS | `deploy/caddy/Caddyfile` matches status 504 in `handle_errors` and serves `maintenance.html`. |
| Upstream dial timeout is short | PASS | The reverse-proxy transport sets `dial_timeout 3s`; the load-balancer retry window is also bounded to 3 seconds. |

**Overall verdict: PASS for the static maintenance contract.** A live degraded-state response still requires the origin and an external vantage point (T038–T040).
