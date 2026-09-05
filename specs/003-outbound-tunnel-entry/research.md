# Phase 0 Research: Zero-Cost Local AI Public Server

**Feature**: `003-outbound-tunnel-entry` | **Date**: 2026-09-06

Resolves every `NEEDS CLARIFICATION` from the plan's Technical Context and records the design decisions the Phase 1 contracts depend on.

---

## R1 — Approved origin operating system

**Status**: **UNRESOLVED BY DESIGN.** This is the one unknown that cannot be closed from the repository.

**Decision**: Treat the origin OS as unverified and build an OS-independent contract. Per-OS operator steps are written provisionally and marked as requiring confirmation on the physical lab server.

**Rationale**: `evidence/public-deployment/operator-inputs.md` records the origin OS as `PENDING` and states explicitly that the machine inspected in this workspace is the GPU laptop, not the origin. Assuming Windows would repeat the error that file was written to correct. The spec now forbids the assumption outright.

**What this actually costs**: Very little. The origin runs exactly two processes — `cloudflared` and a loopback reverse proxy — and both ship first-class Linux and Windows builds. Only three things are genuinely OS-specific:

| Concern | OS-independent part | Deferred until inspection |
|---|---|---|
| Connector startup | `cloudflared` config file and tunnel credentials | service manager unit (`systemd` vs Windows service) |
| Proxy startup | Caddyfile contents | service manager unit and file paths |
| Egress verification | the check itself (see R5) | the command used to run it |

**Alternatives considered**: Assume Windows to match the laptop — rejected, contradicted by evidence and by the spec. Block planning until inspection — rejected, FR-012a requires implementation to continue.

---

## R2 — Origin component set: does the origin still need a reverse proxy?

**Decision**: **Yes.** The origin runs `cloudflared` **plus** Caddy bound to loopback. `cloudflared` forwards to Caddy; Caddy streams to the GPU laptop over the private binding.

**Rationale**: `cloudflared` can forward directly to `http://10.10.0.2:3000`, which would make Caddy look redundant. But five spec requirements have no home if it is removed:

| Requirement | Needs a proxy because |
|---|---|
| FR-014a | Body-size enforcement *during streaming*, without buffering |
| FR-017 / FR-027 | Stripping `X-Job-Token`, `Cookie`, `Authorization` from origin access logs |
| FR-025 | Serving the project-controlled unavailable page when the laptop is unreachable |
| FR-030 | Setting cache-control so job data and artifacts are not stored in shared edge caches |
| Security headers | HSTS, `nosniff`, `DENY`, `no-referrer`, `-Server` |

Feature 002 already implements all five in `deploy/caddy/Caddyfile`. Reusing it is strictly cheaper than reimplementing the behavior as `cloudflared` ingress rules, which cannot express most of it.

**What changes in the Caddyfile**: the public `:443` listener, the `tls` block, the Origin CA certificate, and Authenticated Origin Pulls are all **removed**. With an outbound connector there is no provider-to-origin TLS hop for the origin to authenticate — `cloudflared` owns that. Caddy binds `127.0.0.1` only.

**Net effect on Constitution X**: component count decreases. One inbound listener, one certificate, one client-CA trust store, and their renewal procedures are deleted; one outbound connector is added.

**Alternatives considered**: `cloudflared` direct to the laptop — rejected, loses all five behaviors above. Move Caddy to the laptop — rejected, would put the unavailable-page responsibility on the machine whose absence it must report.

---

## R3 — Streaming pass-through without disk buffering

**Decision**: Caddy `reverse_proxy` in its default streaming mode, with `request_body max_size` retained as an absurdity guard above the application's authoritative 10 MiB limit. Response buffering stays off.

**Rationale**: Caddy's `reverse_proxy` streams request and response bodies by default and only buffers when `buffer_requests` or `buffer_responses` is explicitly enabled. `request_body max_size` rejects an oversized upload during the stream rather than after accumulating it, which is exactly what FR-014a requires. Neither directive writes a spool file.

**Verification approach**: SC-002b is scoped to application- and proxy-authored files, so the test asserts that no new spool or complete-body temporary file appears under the proxy's working and temp directories during a maximum-size transfer. OS paging and provider-internal buffers are explicitly out of scope — they are unobservable and not project-authored.

**Contract obligation**: `tests/security/test_caddy_contract.py` must assert the **absence** of `buffer_requests` and `buffer_responses`. A silent future addition of either would violate FR-014a without any other test failing.

---

## R4 — LAN-only startup independence (the deadlock fix)

**Decision**: All feature 001 services bind loopback and are reachable on the LAN through the existing host-level port forward. The private binding adds a route to the origin; it never gates startup. The WireGuard service dependency is removed from the web service definition.

**Rationale**: The current arrangement is a confirmed FR-037 violation:

- `deploy/windows/services/web.xml` binds Next.js to `10.10.0.2` and declares `<depend>WireGuardTunnel$upstream</depend>`
- `scripts/windows/start_web_service.ps1` additionally polls for the tunnel address and a live handshake before invoking `next start`

Together these mean a WireGuard failure or a laptop reboot while the origin is down leaves the LAN workflow completely unstartable. Feature 002 designed this deliberately — under that architecture the laptop's web entry *was* the public entry — but under feature 003 the public entry moved to the origin, so the binding is now pure downside.

**Target arrangement**, consistent with what feature 001 already does for the API and ComfyUI:

```
Next.js  → binds 127.0.0.1:3000
FastAPI  → binds 127.0.0.1:8000   (already true)
ComfyUI  → binds 127.0.0.1:8188   (already true)
LAN      → host port forward → 127.0.0.1:3000   (already the mechanism)
Origin   → WireGuard 10.10.0.2 → host port forward → 127.0.0.1:3000
```

The origin reaches the same loopback listener through the tunnel address instead of the web service binding to that address directly. Startup order becomes: application first, private binding whenever it is ready, in either order.

**Alternatives considered**: Bind `0.0.0.0` — rejected, exposes the listener on every laptop interface including untrusted networks, which FR-004 forbids. Keep the tunnel binding and add a fallback loopback listener — rejected, two listeners for one service invites divergence.

---

## R5 — Proving the approved address is in the path, per provider

**Decision**: Two distinct evidence methods, selected by which provider is carrying traffic.

| Route | Method | Basis |
|---|---|---|
| **Cloudflare (primary)** | Cloudflare tunnel-connections interface reports the active connector's origin address as the approved address | Documented Cloudflare capability; already specified in FR-002a |
| **zrok (degraded fallback)** | Connector-process locality on the origin **plus** an outbound egress-address check performed **from** the origin | No zrok origin-IP interface is documented; assuming one would violate the spec |

**Rationale**: FR-011e requires the *intent* of FR-002a during fallback but forbids assuming zrok exposes equivalent metadata. The least invasive substitute that actually proves the requirement is a two-part check: the connector process is running on the approved origin, and that origin's outbound path presents the approved address. Combined with the existing tagged-request correlation (SC-002, SC-014c), this establishes that public requests traverse the approved origin before reaching the GPU laptop.

**Explicitly deferred**: binding `cloudflared` to `161.200.90.4` as an explicit source address. FR-002a defers this pending inspection confirming the address is directly bindable. Egress *observation* is non-invasive; source *binding* can break connectivity if the address is a NAT mapping rather than a locally configured address.

**Alternatives considered**: Packet capture on the origin — rejected as more invasive than needed. Trusting the provider dashboard alone during fallback — rejected, no documented field to trust.

---

## R6 — Health-chain layer ordering

**Decision**: Keep the spec's chain order — job service → AI engine → GPU — **unless** an AI-engine-independent GPU probe is adopted, in which case GPU may move above the engine.

**Rationale**: FR-023e makes the ordering conditional on probe independence rather than preference, and the repository shows why. GPU readiness is currently observed through ComfyUI's own `/system_stats` response (`evidence/windows/recovery-matrix.md` records `gpu=cuda:0 NVIDIA GeForce RTX 5070 Laptop GPU` as part of a ComfyUI health line). Reporting GPU as a layer *above* the engine while deriving it from the engine's output would violate FR-023c's rule that a layer must not report healthy on the strength of a layer it did not itself verify.

An independent probe does exist: `nvidia-smi` at the OS level, already used in `evidence/windows/gpu-baseline.md`. Adopting it would make GPU-before-engine legitimate and would improve diagnosis, because a driver fault would then be distinguishable from an engine fault.

**Recommendation for Phase 2**: adopt the `nvidia-smi`-based probe and order GPU above the engine. This is a small task with a real diagnostic payoff, but it is a genuine choice and the contract accommodates either.

---

## R7 — Interim external testing via Quick Tunnel

**Decision**: Quick Tunnel is a valid interim test path for this application, with concurrency evidence excluded.

**Rationale**: Cloudflare documents two quick-tunnel limits — 200 concurrent requests and no Server-Sent Events, because the `trycloudflare.com` edge buffers `text/event-stream`. Neither blinds this project's testing:

- The browser tracks job state by **HTTP polling** (`apps/web/lib/jobs/use-job-status.ts`), not `EventSource`
- The only WebSocket use is the job service's local connection to ComfyUI (`apps/api/src/local3d/adapters/generation/comfy_client.py`), which never crosses the tunnel

So the interim path exercises the same origin pass-through, private binding, and application behavior as production. Only the public name and provider route differ, which is exactly what FR-012b requires.

**Excluded from interim evidence**: concurrency and load behavior. The 200-request ceiling is a quick-tunnel artifact and must not be presented as a production characteristic.

---

## R8 — Zero-cost boundary confirmation

**Decision**: The introduced path is zero project-attributable cost, with two recorded third-party dependencies.

| Dependency | Cost to project | Risk recorded as |
|---|---|---|
| `cloudflared` | $0, Apache-2.0 | — |
| Cloudflare Tunnel + free plan | $0; no paid Access plan needed to publish an application | Provider policy change (FR-034) |
| `twin3dgen.mangosgo.com` | $0 — owned and renewed by a third party | Authorization withdrawal / non-renewal (FR-011c) |
| Visitor TLS certificate | $0, provider-managed, no operator-held secret | — |
| Caddy, WireGuard, WinSW | $0, existing | — |
| zrok fallback | $0, no mandatory card | Interstitial accepted only in degraded mode (FR-011d) |

**Removed cost/complexity**: the Cloudflare Origin CA certificate and Authenticated Origin Pulls trust store from feature 002 are no longer needed, eliminating an operator-managed secret and its renewal.

**Alternatives considered**: partial (CNAME) DNS setup — rejected, Business-plan feature. Paid domain — excluded by owner decision.

---

## Open owner inputs (block cutover only, not implementation)

1. **Hostname authorization** for `twin3dgen.mangosgo.com`, plus route creation in the Cloudflare account managing that zone (FR-011).
2. **Degraded-fallback recovery window** — the maximum time zrok may serve degraded production before an approved stable hostname must replace it (FR-011d). No default is invented here.

## Physical-access items (block cutover only)

1. Origin OS and version (R1).
2. Whether `161.200.90.4` is directly bindable on the origin (R5).
3. The origin's actual outbound egress address (R5).
