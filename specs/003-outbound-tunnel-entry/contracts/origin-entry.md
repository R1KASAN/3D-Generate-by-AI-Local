# Contract: Origin Entry (Connector + Streaming Pass-Through)

**Feature**: `003-outbound-tunnel-entry` | **Date**: 2026-09-06

Replaces feature 002's inbound origin-entry contract. The public application entry is now outbound-initiated, so the origin has **no Internet-facing application or management listener**. The compute-link contract permits one narrowly scoped WireGuard UDP transport listener; it is not part of the public application entry and cannot expose any project service.

---

## O1 — Component layout on the approved origin

```text
Internet ──> provider edge ──> outbound tunnel ──> cloudflared (origin)
                                                        │ loopback HTTP
                                                        ▼
                                                   Caddy (127.0.0.1)
                                                        │ private binding
                                                        ▼
                                              GPU laptop 10.10.0.2:3000
```

| Property | Value | Requirement |
|---|---|---|
| Inbound public application/management ports | **none** | FR-003, FR-004 |
| Private-link transport | Narrowly scoped WireGuard UDP listener only | Compute-link C1a |
| `cloudflared` → proxy | loopback only | FR-004 |
| Proxy listen address | `127.0.0.1` | FR-004 |
| Proxy upstream | GPU laptop over the private binding | FR-014 |
| Origin persistent state | config + redacted logs only | FR-014 |

## O2 — Removed from feature 002

These are **deleted, not reconfigured**. An outbound connector owns the provider hop, so the origin has nothing to authenticate.

| Removed | Why |
|---|---|
| Public `:443` listener | No inbound entry exists (FR-003) |
| `:443` host-guard block | Nothing to guard |
| Cloudflare Origin CA cert + key | No provider→origin TLS hop at the origin |
| Authenticated Origin Pulls CA | Same |
| `ORIGIN_CERT_PATH`, `ORIGIN_KEY_PATH`, `ORIGIN_PULL_CA_PATH` | Secrets no longer exist |

**Consequence for FR-006**: the visitor certificate is provider-managed and the origin holds no certificate secret and no renewal duty.

## O3 — Streaming behavior (FR-014a)

| Property | Required value | Failure mode if wrong |
|---|---|---|
| Request buffering | **off** (`buffer_requests` absent) | 10 MiB spooled to origin disk |
| Response buffering | **off** (`buffer_responses` absent) | Whole artifact spooled; added latency |
| Body size guard | enforced **during** stream, above the app's 10 MiB | Oversize accepted then rejected late |
| Temporary files | none authored by app or proxy | SC-002b failure |

The application on the GPU laptop remains the authoritative enforcer of the 10 MiB policy (FR-019). The proxy limit is an absurdity guard only.

**Test obligation**: assert the **absence** of both buffering directives. Their presence would violate FR-014a while every other test still passed.

## O4 — Header and log hygiene

| Header | Treatment | Requirement |
|---|---|---|
| `X-Job-Token` | removed from access logs | FR-017 |
| `Cookie` | removed from access logs | FR-017 |
| `Authorization` | removed from access logs | FR-017 |

Security headers preserved from feature 002: `Strict-Transport-Security`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `-Server`.

Responses carrying job data or artifacts must not be storable in shared edge caches (FR-030).

Logs correlate by request and Job ID only — no credentials, exact private addresses, uploaded or generated content, or sensitive local paths (FR-027).

## O5 — Unavailable behavior

| Condition | Response | Requirement |
|---|---|---|
| Laptop unreachable, binding down, or job service down — origin healthy | Project-controlled unavailable page, within 5s, no internal address or stack detail | FR-025, SC-008 |
| Origin offline or connector down | Provider's own error response; **no edge-hosted replacement** | FR-025a, SC-008a |

An edge-hosted maintenance page is forbidden: it would serve public traffic without traversing the approved origin (FR-002).

## O6 — Credentials

| Property | Rule |
|---|---|
| Storage | Outside Git, least-privilege file permissions (FR-032) |
| Rotation | Documented revocation and replacement procedure |
| Verification | Revoking the active credential stops traffic; the replacement restores the same hostname without exposing any direct Internet-facing application or management listener (SC-013). The narrowly scoped WireGuard UDP transport listener defined by the Option A compute-link contract (C1a) is explicitly excluded from this prohibition. |

## O7 — Startup

```text
network ready → cloudflared → loopback proxy → readiness verified → local health advertised
```

Readiness must be verified before advertising health (FR-023). The origin's startup **must not** depend on the GPU laptop being reachable — an origin that starts while the laptop is down is the exact condition FR-025 covers.

## O8 — Provider substitution (degraded fallback)

If zrok carries production under FR-011d, this contract is unchanged except:

| Property | Cloudflare | zrok |
|---|---|---|
| Connector process | `cloudflared` | zrok connector |
| Connector host | approved origin | approved origin — **unchanged** |
| Path below the connector | O1 unchanged | O1 unchanged |
| Origin-path evidence | connections interface | locality + egress check |
| TLS-termination disclosure | names Cloudflare | names zrok |

Running the fallback connector on the GPU laptop, or pointing it at the laptop directly, is forbidden (FR-011e).

## Implementation terminology (2026-09-06)

The primary component name is **origin pass-through** (Caddy on the approved origin). The **connector** is cloudflared or the cause-gated zrok replacement. The laptop-facing application role is **job service**. Historical feature-002 web-entry/proxy terminology in superseded records does not change these roles.
