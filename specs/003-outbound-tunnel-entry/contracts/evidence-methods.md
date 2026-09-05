# Contract: Provider-Scoped Evidence Methods

**Feature**: `003-outbound-tunnel-entry` | **Date**: 2026-09-06

Two requirements change shape depending on which provider carries production: proving the approved address is in the path (FR-002a, FR-011e) and disclosing who terminates TLS (FR-018). This contract keeps them from being conflated.

---

## E1 — Origin-path evidence

**Invariant across providers**: the approved origin and the approved address are demonstrably in the public request path, not nominally attached to it.

| | Cloudflare (primary) | zrok (degraded fallback) |
|---|---|---|
| Method | Tunnel-connections interface reports the active connector's origin address | Connector-process locality on the approved origin **plus** an outbound egress-address check run **from** the origin |
| Documented provider support | Yes | **No origin-IP interface documented** |
| Assumption permitted | Read the reported address | **Must not assume** an origin-IP interface exists unless current zrok documentation proves one |
| Criterion | SC-002a | SC-014d |

**Shared corroboration, both providers**: a tagged external request is correlated on the approved origin before the job service handles it (SC-002), and direct probes of the GPU laptop receive no project application response (SC-003, SC-014c).

**Re-capture triggers**: cutover, any origin network-configuration change, and any provider switch.

**Mismatch handling**: blocks cutover, or halts production use if already live, until explained (FR-002a).

## E2 — Source-address binding is deferred

| Action | Status | Gate |
|---|---|---|
| Observe egress address from the origin | **Permitted now** — non-invasive | — |
| Bind the connector's source to the approved address | **Deferred** | Physical inspection confirming the address is directly bindable |

Binding a source address that is a NAT mapping rather than a locally configured address breaks connectivity. Observation carries no such risk, which is why FR-002a separates them. Choose the least invasive method that proves the requirement.

## E3 — TLS-termination disclosure (FR-018)

| Property | Rule |
|---|---|
| Named party | Whichever provider **currently** carries traffic |
| Primary route | Cloudflare |
| Degraded fallback | **zrok** — recorded separately, with its own logging and privacy characteristics |
| Forbidden | Claiming end-to-end token non-observation under any provider |
| Forbidden | Continuing to name Cloudflare while zrok carries live traffic (SC-014e) |

The project may claim only that no **project-controlled** log contains the token, and must state where that claim's boundary lies (Constitution III).

**Owner acceptance is per provider.** Cloudflare's residual exposure is accepted for the primary route. zrok's must be recorded and accepted **before** the fallback carries production — it is not covered by the existing acceptance.

## E4 — Fallback activation is cause-gated (FR-011d)

| Cause | Fallback permitted | Public release |
|---|---|---|
| Hostname **never authorized** before cutover | **No** | Blocked; LAN-only. zrok and Quick Tunnel serve dev/demo only |
| Already-live hostname **later withdrawn** | **Yes** | Degraded production; interstitial accepted |

Activation requires recording cause, start time, and the owner-defined recovery window. **That window is an owner input and has not been supplied** — it must exist before first reliance (FR-011d).

The fallback must never silently become the permanent production identity.

## E5 — Evidence hygiene

| Rule | Requirement |
|---|---|
| Addresses masked in evidence files | existing repository practice |
| No capability token in any evidence artifact | SC-009 |
| No uploaded or generated content | FR-027 |
| Existing masking tests continue to pass | `tests/security/test_evidence_masking.py` |

## E6 — Cutover evidence set

| Evidence | Criterion |
|---|---|
| External user journey completed off-LAN | SC-001 |
| Approved-origin traversal correlated | SC-002 |
| Connector origin address matches (provider-appropriate method) | SC-002a / SC-014d |
| No request or response body spooled by app or proxy | SC-002b |
| No direct application response from any internal interface | SC-003 |
| DNS reveals no origin address | SC-004 |
| Zero recurring cost; no card; no billable fallback | SC-005 |
| Reboot and recovery matrix across both machines | SC-006 … SC-006e |
| Compute-unavailable and origin-down behavior | SC-008, SC-008a |
| Token absent from all project-controlled logs | SC-009 |
| Hostname authorization and continuity path | SC-014 |
| Fallback reachable, not in production path, cause-gated rehearsals | SC-014a, SC-014b |
| TLS-termination party named correctly for the active provider | SC-014e |
