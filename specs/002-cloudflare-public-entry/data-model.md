# Phase 1 Data Model: Request Path, Trust Boundaries, and Availability State

**Feature**: `002-cloudflare-public-entry` | **Date**: 2026-09-05

This feature introduces no application data. What it does introduce is a **request path with three trust boundaries** and an **availability state machine** whose transitions the operator and the verification scripts both need to reason about. Those are modelled here.

---

## 1. Entities

### Published name

| Field | Value / rule |
|---|---|
| Form | A single subdomain of an owner-registered zone |
| DNS hosting | Cloudflare |
| Proxy status | **Proxied** (required) |
| Resolves to | Cloudflare anycast addresses — never the origin address (FR-001b) |
| Owned by | The operator, personally (owner decision, 2026-09-05) |
| Stability | MUST NOT change when the GPU laptop relocates (FR-004) |

### Origin

| Field | Value / rule |
|---|---|
| Address | `161.200.90.4` — the only permitted address (FR-025) |
| Excluded address | `161.200.90.3` — MUST NOT appear in `deploy/**` or any network-applying script, and MUST NOT be probed |
| Role | TLS termination for the provider hop, path routing, unavailability notice, credential forwarding |
| Certificate | Cloudflare Origin CA (R1) — not publicly trusted, not publicly validated |
| Accepts | Only connections presenting a valid Cloudflare client certificate (R3) |
| Relocatable | **No.** Must stay powered and hold the allocated address |

### Compute link

| Field | Value / rule |
|---|---|
| Protocol | WireGuard, 51820/udp |
| Initiated by | The GPU laptop, outbound (FR-016) |
| Endpoint in laptop config | Address literal `161.200.90.4:51820` — never a hostname (R5) |
| Tunnel addresses | Origin `10.10.0.1`, laptop `10.10.0.2` |
| Peer scope | `/32` on both sides — never a wide range, never a default route |
| Keepalive | Set on the laptop side only (the side behind NAT) |

### GPU laptop

| Field | Value / rule |
|---|---|
| Web entry binding | `10.10.0.2:3000` — the tunnel address, never a wildcard (FR-024) |
| Backend binding | `127.0.0.1:8000` — loopback only |
| Engine binding | `127.0.0.1:8188` — loopback only, never reachable from the origin |
| Relocatable | **Yes.** This is the point of the design |

### Job credential

| Field | Value / rule |
|---|---|
| Carrier | Request header, for the full length of the path |
| Transformation | **None permitted** — not stripped, rewritten, or renamed (FR-010) |
| In URLs | **Never** (FR-012) |
| In project-controlled logs | **Never** — origin and application logs (FR-011) |
| At the proxy layer | Handled in cleartext by design, since that tier terminates TLS. Logging suppressed wherever a control exists; residual recorded as evidence (FR-011a). The project must not claim end-to-end non-logging (FR-011b) |
| Scope | Exactly one job |

---

## 2. Request path and trust boundaries

```
  Visitor
    │  TLS #1 — provider-managed certificate, auto-renewed
    ▼
┌─────────────────────────── Boundary A ───────────────────────────┐
│ Cloudflare edge                                                  │
│   · terminates visitor TLS          · redirects HTTP → HTTPS     │
│   · enforces 100 MB body ceiling    · presents client cert       │
└──────────────────────────────────────────────────────────────────┘
    │  TLS #2 — Origin CA cert, validated by provider (Full strict)
    │           + provider client cert, validated by origin (mTLS)
    ▼
┌─────────────────────────── Boundary B ───────────────────────────┐
│ Origin  161.200.90.4                                             │
│   · refuses any client without the provider cert                 │
│   · 12 MB absurdity guard      · routes by path                  │
│   · serves unavailability notice when upstream is down           │
│   · forwards job credential untouched, logs it nowhere           │
└──────────────────────────────────────────────────────────────────┘
    │  WireGuard, key-authenticated, /32 peer scope
    ▼
┌─────────────────────────── Boundary C ───────────────────────────┐
│ GPU laptop  10.10.0.2                                            │
│   Next.js :3000  ──internally──▶  FastAPI 127.0.0.1:8000         │
│                                        │                         │
│                                        ▼                         │
│                          ComfyUI 127.0.0.1:8188                  │
│                          (never reachable across Boundary B)     │
└──────────────────────────────────────────────────────────────────┘
```

**What each boundary is actually protecting:**

- **A** — the only boundary a visitor sees. Its job is to make the origin unnecessary to know about.
- **B** — the load-bearing security boundary. Everything that keeps the service from being reachable directly at `161.200.90.4` lives here. Concealment of the address is *not* part of this boundary; the mTLS check and the firewall scope are.
- **C** — unchanged by this feature. The engine's isolation is a property of the laptop's own bindings, not of anything upstream.

**Why the API is not split onto its own port:** Constitution Principle III permits one Internet-facing port. Independently, the backend carries no cross-origin permissions, so a second origin would cause the browser to block the application's own requests. Path routing at Boundary B satisfies both. `/api/*` reaches the backend through the laptop's existing internal forwarding — the origin never connects to `:8000` itself.

---

## 3. Availability states

The two machines fail differently, and conflating them is the mistake this section exists to prevent.

| State | Origin | Compute link | Laptop | Visitor sees |
|---|---|---|---|---|
| `SERVING` | up | up | up | The application |
| `DEGRADED` | up | down or laptop down | any | Unavailability notice, valid TLS, name resolves |
| `DOWN` | **down** | any | any | Provider error — name resolves, application does not respond |

**Transitions**

```
SERVING ──laptop sleeps / loses network / reboots──▶ DEGRADED
DEGRADED ──laptop reconnects, tunnel re-establishes──▶ SERVING   (automatic, ≤5 min, SC-008)
SERVING ──origin loses power or connectivity──▶ DOWN
DOWN ──origin restored──▶ SERVING or DEGRADED
```

**The asymmetry that matters**: `DEGRADED` is an expected, routine state — it is what mobility looks like from outside, and the design treats it as normal operation. `DOWN` is an incident. The origin is a single point of failure that this feature does not mitigate; making the laptop relocatable does not make the origin redundant.

**Recovery must act on the failing layer only.** A stale tunnel and a dead web process produce the same visitor-facing symptom but require opposite remedies; restarting the web process cannot fix a dead tunnel, and will loop forever if used as the response to one. Recovery therefore diagnoses first (FR-019), enforces a cooldown, and escalates after a bounded number of attempts rather than retrying indefinitely (FR-020).

---

## 4. Validation rules

| Rule | Source | Verified by |
|---|---|---|
| Published DNS must not disclose the origin address | FR-001b | `scripts/verify/test_dns_disclosure.py` |
| Direct request to the origin address must be refused | FR-005 | `scripts/verify/test_origin_lockdown.py` |
| Inbound 443 scoped to provider ranges; 80 not open; 51820/udp open | FR-005a, R4, R6 | `deploy/firewall/verify-public-edge.ps1` |
| Provider-to-origin hop encrypted **and** validated | FR-003a | `scripts/verify/test_https_boundary.py` |
| Origin certificate needs no public validation path | FR-003b | Config review + absence of any ACME directive |
| Job credential unmodified end to end | FR-010 | `scripts/verify/test_public_auth.py` |
| Job credential absent from every **project-controlled** log | FR-011 | Log grep: origin access/error logs + application logs |
| Provider-side credential logging suppressed where a control exists; residual exposure recorded | FR-011a, FR-011b | `evidence/public-deployment/residual-exposure.md`, reviewed against Constitution III v1.2.0 |
| Origin certificate issue and expiry dates recorded | FR-003c | `docs/operations/naming-continuity.md`, `cloudflare-setup.md` |
| Laptop web-entry port refused from the laptop's own physical LAN | FR-009, FR-024 | `scripts/verify/test_upstream_lan_lockdown.py` |
| Missing and wrong credentials indistinguishable from nonexistent job | FR-013 | `scripts/verify/test_public_auth.py` |
| Origin guard rejects any address other than `161.200.90.4` | FR-025 | `tests/security/test_caddy_contract.py` + script guard |
| `161.200.90.3` absent from `deploy/**` and network scripts | FR-025 | `tests/security/test_caddy_contract.py` |
| Internals unreachable externally | FR-009 | `scripts/verify/test_external_ports.py` |
| Compute link survives relocation and reboot | FR-017, FR-018 | `scripts/verify/test_mobility.py` |
| Naming continuity documented sufficiently for handover | FR-029 | `docs/operations/naming-continuity.md`, reviewed per SC-013 |
