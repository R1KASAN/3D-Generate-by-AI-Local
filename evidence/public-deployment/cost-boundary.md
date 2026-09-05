# Cost Boundary Record — Feature 003

**Feature**: `003-outbound-tunnel-entry` | **Task**: T042 | **Recorded**: 2026-09-06

Every dependency introduced by the outbound-tunnel architecture, per [research.md R8](../../specs/003-outbound-tunnel-entry/research.md) and the spec's cost gate (FR-007, FR-008, SC-005). This record is machine-checkable via `scripts/verify/test_cost_boundary.py --cost-record cost-boundary.json`.

## What changed from feature 002

Feature 002's Cloudflare Origin CA certificate and Authenticated Origin Pulls (mTLS) trust store are **removed**, not replaced — the outbound connector eliminates the provider-to-origin TLS hop that made them necessary. This is a net reduction in operator-managed secrets, not a like-for-like swap.

## Dependency table

| Dependency | Recurring price | Payment card required | Paid fallback enabled | Notes |
|---|---|---|---|---|
| `cloudflared` (connector software) | $0 | No | No | Apache-2.0, self-hosted binary |
| Cloudflare Tunnel (free plan) | $0 | No | No | No paid Access plan needed to publish an application |
| `twin3dgen.mangosgo.com` | $0 | No | No | Owned and renewed by a third party at no cost to this project — see [operator-inputs.md](operator-inputs.md); **pending written authorization** |
| Visitor TLS certificate | $0 | No | No | Provider-managed; origin holds no certificate secret |
| Caddy (loopback pass-through) | $0 | No | No | Existing, reused from feature 002 with its inbound half removed |
| WireGuard (private binding) | $0 | No | No | Existing, unchanged from feature 002 |
| WinSW (service supervision) | $0 | No | No | Existing |
| zrok (degraded-production fallback) | $0 | No | No | No card required for interstitial-accepting free tier; a card would remove the interstitial but is not required and MUST NOT be added |

## Removed (no longer a dependency)

| Removed item | Why it no longer counts |
|---|---|
| Cloudflare Origin CA certificate | No provider-to-origin TLS hop exists under the outbound design |
| Authenticated Origin Pulls (mTLS) | Same — the connector owns the provider-facing hop instead |

## Verification

```bash
python scripts/verify/test_cost_boundary.py --cost-record evidence/public-deployment/cost-boundary.json
```

**Overall verdict: PASS** — every entry is $0 recurring, requires no payment card, and enables no paid fallback (SC-005). The `mangosgo.com` hostname's authorization is a separate, outstanding **owner input** (FR-011, T045), not a cost-boundary failure: authorization being pending does not mean the dependency costs anything once granted.
