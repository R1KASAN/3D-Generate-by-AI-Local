# Phase 1 Data Model: Zero-Cost Local AI Public Server

**Feature**: `003-outbound-tunnel-entry` | **Date**: 2026-09-06

This feature adds **no application data entities**. Feature 001's `Generation Job`, `Job Artifact`, job state machine, SQLite schema, and per-job capability tokens are carried forward unchanged and are authoritative.

What follows are **deployment and evidence entities** — configuration and records the deployment layer owns.

---

## Deployment entities

### PublicHostname

The browser-facing address, obtained at no project cost.

| Field | Type | Rules |
|---|---|---|
| `fqdn` | string | Preferred: `twin3dgen.mangosgo.com` |
| `state` | enum | `candidate` → `authorized` → `live` → `withdrawn` |
| `domain_owner` | string | Third party; not the project |
| `managing_account` | string | Cloudflare account holding the zone |
| `authorization_record` | reference | Written evidence; verbal permission is insufficient (FR-011) |
| `project_cost` | fixed | Always `0`. A non-zero value fails the cost gate |

**Transitions**: `candidate → authorized` requires a written authorization record. `authorized → live` requires a working tunnel route. `live → withdrawn` triggers the FR-011d fallback path. **`candidate → withdrawn` does not enable the fallback** — never-authorized keeps the public release blocked.

---

### TunnelConnector

The outbound relationship between the approved origin and the provider edge.

| Field | Type | Rules |
|---|---|---|
| `provider` | enum | `cloudflare` (primary) or `zrok` (degraded fallback) |
| `host` | fixed | The approved origin. Running on the GPU laptop is forbidden (FR-011e) |
| `direction` | fixed | Outbound-initiated. No inbound port (FR-003) |
| `credential_location` | path | Outside Git, least-privilege (FR-032) |
| `start_policy` | enum | Automatic on boot, dependency-ordered (FR-023) |
| `revocation_state` | enum | `active` / `revoked` / `replaced` |

**Invariant**: exactly one provider carries production at a time. Both connectors running simultaneously is a misconfiguration, because origin-path evidence and TLS-termination disclosure are provider-scoped.

---

### OriginPassThrough

The stateless streaming proxy on the approved origin.

| Field | Type | Rules |
|---|---|---|
| `listen_address` | fixed | Loopback only. No public listener (FR-003, FR-004) |
| `upstream` | address | GPU laptop over the private binding |
| `buffering` | fixed | Disabled for both request and response bodies (FR-014a) |
| `body_limit` | bytes | Absurdity guard above the application's authoritative 10 MiB |
| `log_redaction` | list | `X-Job-Token`, `Cookie`, `Authorization` removed (FR-017) |
| `persistent_state` | fixed | None. No job state, uploads, or artifacts (FR-014) |

**Invariant**: the only files this component creates are configuration and redacted logs. Any artifact spool or complete-body temporary file is a defect (SC-002b).

---

### PrivateBinding

The narrow origin-to-laptop link, carried forward from feature 002.

| Field | Type | Rules |
|---|---|---|
| `peer_scope` | fixed | Single-peer `/32` on each side. Never `0.0.0.0/0` |
| `origin_address` | address | `10.10.0.1` |
| `laptop_address` | address | `10.10.0.2` |
| `gates_app_startup` | fixed | **`false`** — this is the FR-023d fix |
| `reconnect` | policy | Automatic with bounded backoff, asynchronous to app startup |

**Changed from feature 002**: `gates_app_startup` was effectively `true` (service dependency plus address binding). It is now `false`.

---

### HealthLayer

One independently reportable link in the FR-023c chain.

| Field | Type | Rules |
|---|---|---|
| `name` | enum | `edge`, `origin_connector`, `private_binding`, `job_service`, `ai_engine`, `gpu` |
| `probe` | reference | Must not depend on a layer it does not itself verify (FR-023c) |
| `owner_machine` | enum | `origin` or `laptop` |
| `state` | enum | `healthy` / `degraded` / `failed` / `unknown` |
| `consecutive_failures` | int | Recovery stops at 3 at the same layer (FR-024) |

**Ordering rule**: `gpu` may precede `ai_engine` only if its probe is engine-independent (FR-023e). See `contracts/health-chain.md`.

---

## Evidence entities

### OriginPathEvidence

Proof that the approved address is functionally in the public path.

| Field | Type | Rules |
|---|---|---|
| `provider` | enum | Determines the method — the two are not interchangeable |
| `method` | enum | `cloudflare_connections_api` or `origin_locality_plus_egress_check` |
| `approved_address_observed` | bool | Mismatch blocks or halts production (FR-002a) |
| `captured_at` | timestamp | Re-captured after any origin network change |

**Rule**: the zrok method must not assume a provider origin-IP interface unless current documentation proves one exists (SC-014d).

---

### ResidualExposureRecord

Which third party can observe forwarded request content.

| Field | Type | Rules |
|---|---|---|
| `tls_terminating_party` | enum | Whichever provider currently carries traffic |
| `observable` | list | Forwarded request content including capability tokens |
| `claim_limit` | fixed | No end-to-end non-observation claim permitted (FR-018) |

**Rule**: while zrok carries live traffic, this record names zrok. Continuing to name Cloudflare in that period is a defect (SC-014e).

---

### DegradedProductionRecord

Created only when the zrok fallback carries production.

| Field | Type | Rules |
|---|---|---|
| `cause` | enum | Only `hostname_withdrawn`. `never_authorized` must not produce this record |
| `started_at` | timestamp | Required |
| `recovery_window` | duration | **Owner input — not yet supplied.** Must be recorded before first reliance (FR-011d) |
| `interstitial_accepted` | bool | `true` for the degraded period only |

---

### CostBoundaryRecord

| Field | Type | Rules |
|---|---|---|
| `dependency` | string | Every introduced dependency |
| `recurring_price` | fixed | Must be `0` |
| `payment_card_required` | fixed | Must be `false` |
| `paid_fallback_enabled` | fixed | Must be `false` |

---

## Relationships

```text
PublicHostname ──selects──> TunnelConnector ──runs on──> Approved Origin
                                  │
                                  ├──> OriginPathEvidence     (method keyed by provider)
                                  └──> ResidualExposureRecord (party keyed by provider)

Approved Origin ──> OriginPassThrough ──> PrivateBinding ──> GPU Laptop
                                                                  │
                                                                  └──> Feature 001 (unchanged)

HealthLayer[6] spans both machines; each layer owned by exactly one machine.
```
