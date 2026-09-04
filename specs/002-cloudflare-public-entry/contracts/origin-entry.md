# Contract: Origin Entry Behaviour

**Feature**: `002-cloudflare-public-entry` | **Date**: 2026-09-05

What the origin reverse proxy at `161.200.90.4` MUST accept, reject, transform, and log. Asserted by `tests/security/test_caddy_contract.py` (static) and `scripts/verify/*` (runtime).

---

## C1 — Connection admission

| Condition | Required behaviour |
|---|---|
| Valid Cloudflare client certificate presented | Accept |
| No client certificate | **Reject at TLS handshake** — do not serve, do not redirect, do not return an application error page |
| Client certificate present but not from the provider CA | Reject at handshake |
| Source address outside provider ranges | Rejected by firewall before reaching the proxy |
| Host header not the published subdomain | **404**, application not served |
| Request addressed to the bare origin address | **404**, application not served |

Handshake-level rejection matters: an application-layer 403 confirms to a prober that a service is present. A refused handshake reveals materially less.

## C2 — TLS

| Property | Required |
|---|---|
| Origin certificate | Cloudflare Origin CA, loaded from file |
| ACME / automatic certificate management | **MUST be absent.** No `email` directive, no ACME issuer, no public CA client |
| Client certificate verification | **Required**, against the provider's origin-pull CA |
| Listener on port 80 | **MUST NOT exist** |

`admin off` remains required — no remote administration API on the origin.

## C3 — Routing

| Path | Destination | Notes |
|---|---|---|
| `/api/*` | Laptop web entry over the tunnel | Reaches the backend via the laptop's own internal forwarding — the origin never connects to `:8000` |
| everything else | Laptop web entry over the tunnel | |
| any path | **Never** the engine on `:8188` | Not reachable, not configurable |

Upstream MUST be the tunnel address only. `0.0.0.0`, `::`, any wildcard, any literal public address, and `:8188` are all forbidden as upstreams.

## C4 — Request body

| Property | Value | Reason |
|---|---|---|
| Origin limit | 12 MB | Absurdity guard only |
| Authoritative policy | 10 MiB, enforced by the application | Application returns the branded, explanatory error (FR-015) |
| Provider ceiling | 100 MB | Confirmed (R8); no configuration needed |

The origin limit is deliberately above the application's so multipart framing overhead never causes the network layer to reject a file the application would have accepted.

## C5 — Header handling

| Header | Required behaviour |
|---|---|
| Job credential header | Forwarded **byte-identical**. Never stripped, rewritten, renamed, or added |
| `Strict-Transport-Security` | Set |
| `X-Content-Type-Options: nosniff` | Set |
| `X-Frame-Options: DENY` | Set |
| `Referrer-Policy: no-referrer` | Set |
| `Server` | Removed |

## C6 — Logging

| Field | Required behaviour |
|---|---|
| Job credential header | **Deleted from log output** |
| `Cookie`, `Authorization` | Deleted |
| Request path | Logged — and must never contain a credential, since credentials never appear in URLs (FR-012) |

The credential deletion must be explicit. Automatic redaction covers `Authorization` and `Cookie` only; an arbitrary header lands in the log in cleartext unless deleted by name. This is the single most likely silent violation in the whole configuration, which is why a log grep for a known credential value is a required acceptance check (SC-006) rather than a code review item.

## C7 — Unavailability behaviour

| Condition | Required behaviour |
|---|---|
| Upstream unreachable (502/503/504) | Serve the purpose-written unavailability notice |
| Any other error | Ordinary error response |
| During unavailability | Name resolves, TLS valid — the domain must never appear broken or unclaimed |
| Upstream returns | Application served again with no operator action |

Upstream dial and health-check timeouts must be short. The laptop being unreachable is an expected routine state produced by mobility, not an incident to hang a request on.

## C8 — Address restriction

| Rule | Enforcement |
|---|---|
| `161.200.90.4` is the only permitted origin address | Hard refusal in the configuration script — not a parameter default |
| `161.200.90.3` MUST NOT appear in `deploy/**` or any network-applying script | Static test |
| `161.200.90.3` MUST NOT be probed by any verification script | Static test |
| `161.200.90.3` MAY appear in `docs/**`, `evidence/**`, and in the tests asserting its exclusion | Scope limit — a repository-wide ban would fail against the project's own documentation of the restriction |
