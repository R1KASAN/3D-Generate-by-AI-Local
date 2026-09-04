# Quickstart: Validating the Cloudflare Public Entry

**Feature**: `002-cloudflare-public-entry` | **Date**: 2026-09-05

How to prove this feature works end to end. Implementation steps live in `tasks.md`; this is the validation guide.

---

## Prerequisites

**Before any cutover step** — these are gates, not a checklist to work around:

| Gate | Detail |
|---|---|
| Owner gate updated | `evidence/public-deployment/owner-gate.md` records the mode and ownership decisions of 2026-09-05. The model-license and permitted-territory decision inherited from feature 001 is **still open** and still blocks public exposure. |
| Inbound permissions confirmed **in writing** | `443/tcp` from provider ranges, `51820/udp` from any. Port 80 not requested. See [`contracts/port-policy.md`](./contracts/port-policy.md). Late discovery of a third permission is a planning defect (FR-030). |
| Management path decided and proven | Port and source range chosen, listener running, access confirmed from that source — **before** default-deny is applied. |
| Operator inputs supplied | Origin OS and version; domain name; confirmation the origin holds `161.200.90.4`; confirmation nothing else listens on 443. |
| External vantage point | Mobile data or an off-campus host. Verification from inside the university network is not evidence (FR-027). |
| Second host on the laptop's network | Needed for the SC-015 lockdown probe. Run it at least once on a network the laptop does not own — a hotspot or public Wi-Fi — since that is the case the scoping protects against. |
| Constitution v1.2.0 in force | The residual-exposure clause governing a TLS-terminating proxy must be the amended version. Auditing against v1.1.0 would fail this design for a reason the owner has already resolved. |

## Setup order

Provider-side first, so the origin is never briefly reachable in an unprotected state.

1. **Provider**: add the zone, create the subdomain record **proxied**, set SSL mode **Full (strict)**, enable **Authenticated Origin Pulls**, issue an **Origin CA certificate**.
2. **Origin**: install the Origin CA certificate and key; configure the reverse proxy to require and verify the provider client certificate; no ACME, no port 80 listener.
3. **Origin firewall**: apply the policy from `contracts/port-policy.md`. Confirm management access from a *new* connection before ending the session.
4. **Laptop**: tunnel config with `/32` peer scope and keepalive; startup wrapper that waits for the tunnel address and a live handshake; recovery watchdog.
5. **Verify** in the order below.

---

## Validation

Run from the repository root. Python checks use the project's environment:

```bash
uv run --project apps/api pytest tests/security/test_caddy_contract.py -v
```

### Stage 1 — Static, before anything is exposed

| Check | Expected |
|---|---|
| `tests/security/test_caddy_contract.py` | Passes: **no `basic_auth` (preserved assertion, FR-023)**, no ACME directive, no `:80` listener, client-certificate verification present, credential deleted from logs, upstream is the tunnel address only, `161.200.90.3` absent from `deploy/**` |
| Reverse-proxy config validation | Config parses and validates |

### Stage 2 — Boundary, from an external vantage point

| Check | Script | Expected |
|---|---|---|
| Secure entry | `scripts/verify/test_https_boundary.py` | 443 returns 2xx, chain valid, hostname matches, no warning |
| Insecure redirect | same | HTTP redirects to HTTPS at the provider edge |
| Origin not disclosed | `scripts/verify/test_dns_disclosure.py` | Published records resolve to provider addresses, never `161.200.90.4` |
| Origin refuses direct traffic | `scripts/verify/test_origin_lockdown.py` | Connecting straight to the origin address is refused at handshake |
| Internals unreachable | `scripts/verify/test_external_ports.py` | 3000, 8000, 8188, 3389, 2019 all unreachable |
| Port 80 closed | same | No listener, no rule |
| Compute link — negative | `scripts/verify/test_wireguard_reachability.py` | Unauthenticated UDP gets no response |
| Compute link — **positive** | same | Real peer handshakes, timestamp fresh, origin reaches `10.10.0.2:3000` |
| Laptop boundary | `deploy/firewall/verify-upstream-boundary.ps1` | Port 3000 scoped to `10.10.0.1/32` on the tunnel interface; 8000, 8188, 3389 blocked |
| Laptop refused from its own LAN | `scripts/verify/test_upstream_lan_lockdown.py` | Connection refused from a second host on the laptop's physical network (SC-015) |

The positive compute-link check is the one that proves the UDP permission actually traverses the border firewall. A silent port and a blocked port look identical from outside, so the negative check alone proves nothing about the permission.

### Stage 3 — Full journey

| Check | Script | Expected |
|---|---|---|
| Upload → generate → preview → download | `scripts/verify/test_external_acceptance.py` | Completes; downloaded model byte-identical to the server's copy |
| Credential isolation | `scripts/verify/test_public_auth.py` | Missing credential, another job's credential, and a nonexistent job all produce identical responses |
| Credential never in URLs | same | No credential appears in any request line |
| Credential never in project-controlled logs | log grep: origin access/error + application logs | Zero matches for a known credential value (SC-006) |
| Provider exposure recorded | review `evidence/public-deployment/residual-exposure.md` | Provider named, TLS termination stated, logging controls listed with the setting applied to each (SC-006a) |
| Oversized upload | `test_external_acceptance.py` | Rejected by the **application** with its explanatory error, not by the network layer |

### Stage 4 — Mobility and recovery

This is what distinguishes the feature from an ordinary deployment. **No DNS record, proxy configuration, or tunnel address may be edited at any point during Stage 4.**

| Step | Expected |
|---|---|
| Full journey with the laptop on the university network | Succeeds |
| Move to mobile hotspot, wait for reconnect, repeat | Succeeds, no configuration touched |
| Move to a home network, repeat | Succeeds, no configuration touched |
| **Reboot the laptop off-campus — at least 3 consecutive trials** | Full chain returns unattended each time (SC-003) |
| Disconnect the laptop | Unavailability notice; name still resolves; TLS still valid |
| Reconnect | Application served again within 5 minutes, no operator action (SC-008) |
| Power the laptop off for 30 minutes, then on | Tunnel re-establishes unattended |

Three reboot trials rather than one because the startup-ordering defect this guards against is a race: it fails intermittently, and a single passing run is not evidence.

### Stage 5 — Governance

| Check | Expected |
|---|---|
| Evidence review | Every artifact masks addresses; no credential material anywhere (SC-010) |
| Continuity handover | Someone other than the operator can state, from documentation alone, where the domain is registered, which account controls it, when it and the Origin CA certificate renew, and how to restore reachability without the operator (SC-013, SC-014) |
| Residual exposure | `evidence/public-deployment/residual-exposure.md` satisfies all four conditions of Constitution Principle III v1.2.0, and no project document claims end-to-end credential non-logging (SC-006a, FR-011b) |

---

## Rollback

| Situation | Action |
|---|---|
| Provider layer misbehaving, origin healthy | Set the DNS record to unproxied. **Only if** the origin has a publicly trusted certificate and 443 is reachable — under this design it has neither, so treat this as unavailable rather than as a rollback path |
| Origin misconfigured after cutover | Revert reverse-proxy config; restart; the provider returns an error page and no traffic reaches a half-configured origin |
| Locked out of the origin | Physical console. This is why the management path must be proven before default-deny is applied |
| Need to withdraw entirely | Remove the DNS record. The name stops resolving; nothing is exposed |

Certificate transparency has no rollback: once the visitor-facing certificate is issued, the subdomain is permanently discoverable in public CT logs. Confirm the owner accepts this before the first proxied request, because it cannot be undone afterwards.
