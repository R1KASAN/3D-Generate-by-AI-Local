# Degraded-Production Fallback Policy — zrok

**Feature**: `003-outbound-tunnel-entry` | **Tasks**: T046, T047, T048 | **Recorded**: 2026-09-06

Per FR-011d, zrok is a cause-gated fallback: it must never carry production if `twin3dgen.mangosgo.com` was never authorized, and may carry **degraded** production only if an already-live production hostname is later withdrawn.

## T047 — zrok's zero-cost status, hostname format, interstitial behavior, quota

| Property | Finding | Source |
|---|---|---|
| Plan | FREE, $0/month | [zrok pricing](https://zrok.io/pricing/) |
| Payment card | Not required to operate. "Start sharing instantly. Add a credit card anytime to remove interstitial pages." | zrok pricing |
| Hostname format | `https://<name>.share.zrok.io` (namespace `public` = `share.zrok.io`) | [zrok namespaces](https://netfoundry.io/docs/zrok/concepts/namespaces/) |
| Name persistence | Reserved names survive restart in v2.0.4+ (fixes an agent bug that previously deleted reserved shares on shutdown) | [zrok CHANGELOG](https://github.com/openziti/zrok/blob/main/CHANGELOG.md) |
| Interstitial | Shown on first visit per week to free-tier accounts without a verified card. Bypass: `skip_zrok_interstitial` HTTP header, settable by the application's own requests | [zrok interstitial docs](https://netfoundry.io/docs/zrok/self-hosting/frontends/interstitial-page/) |
| Daily quota | 5 GB/day (rolling 24h window); exceeding it disables running shares until usage falls back under the limit | zrok pricing / service limits |
| Rate limits | 2,000 req/300s per IP; 7,500 req/300s per share | [zrok service limits](https://netfoundry.io/docs/zrok/myzrok/service-limits/) |
| Realistic sufficiency | Repository evidence shows generated artifacts of ~3.5-5.3 MiB ([textured-glb-validation.md](../windows/textured-glb-validation.md), [windows-gpu-validation.md](../../docs/operations/windows-gpu-validation.md)) against a 10 MiB upload cap — worst case ≈248 jobs/day, typical ≈568 jobs/day within the 5 GB quota | Repository evidence + FR-019 upload limit |

**Conclusion for T047**: zrok is genuinely zero-cost with no mandatory card, and its quota comfortably covers this project's realistic load. This confirms the feasibility finding already recorded in the spec's Clarifications session (2026-09-06).

## T048 — TLS-termination and privacy characteristics, separate from Cloudflare's

Per Constitution III and FR-018, the residual-exposure record must name whichever provider is actually terminating TLS. While the zrok fallback carries live traffic, that party is **zrok**, not Cloudflare — and its characteristics have not been formally accepted by the owner as a separate residual exposure.

| Property | Finding |
|---|---|
| TLS termination | zrok's edge frontend (`share.zrok.io`) terminates TLS, analogous to Cloudflare's role for the primary route |
| Traffic visibility | zrok, as the TLS-terminating party, can observe forwarded request content while the fallback is active — the same category of residual exposure Cloudflare has for the primary route |
| Logging control | Not yet independently verified from zrok's own documentation whether request-level provider logging can be disabled the way Cloudflare's can be configured. **Requires operator verification on zrok's own account before this gap can close.** |

**Status: BLOCKED on owner input.** Per Constitution III, an owner-approved third-party TLS-terminating proxy is permitted only under four conjunctive conditions (written owner approval; provider-side credential logging disabled wherever that control exists; the exposure recorded naming the provider; encrypted and certificate-validated proxy-to-origin hop). Only the "recorded, naming the provider" condition is satisfied by this document. The written owner approval and the logging-control verification remain outstanding and **must be completed before the zrok fallback is relied upon for real degraded production**, not merely before it is first tested.

## T046 — Owner-defined recovery window

**Status: BLOCKED on owner input.** FR-011d requires an explicit maximum duration the zrok fallback may serve degraded production before an approved stable hostname must replace it. No value has been supplied. This section stays a placeholder — do not infer a default; record the owner's actual figure here when given, e.g.:

```
Recovery window: <N> days from DegradedProductionRecord.started_at
Decided by: <owner>, <date>
Rationale: <why this window>
```

## What remains before the fallback may be relied upon

1. Owner supplies the recovery window (T046).
2. Owner reviews and accepts zrok's residual TLS exposure in writing, per Constitution III (T048).
3. Operator verifies whether zrok exposes a provider-side logging-suppression control, and uses it if available (T048, Constitution III "wherever that control exists").

None of these block **implementation or rehearsal** of the fallback mechanism itself (T049-T052) — only reliance on it for genuine degraded production.
