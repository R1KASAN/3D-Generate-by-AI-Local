# Contract: Compute Link (Approved Origin ↔ GPU Laptop)

**Feature**: `003-outbound-tunnel-entry` | **Date**: 2026-09-06

Revises feature 002's compute-link contract. The addressing, scope, and persistence rules carry forward unchanged. **Startup ordering and role naming change**, because the public entry moved from the laptop to the approved origin.

---

## C1 — Direction and addressing (unchanged from feature 002)

| Property | Value | Why |
|---|---|---|
| Initiator | **The laptop**, outbound | The laptop needs no inbound reachability on any network it joins |
| Responder | The origin, `51820/udp` | The origin has a stable address; the laptop does not |
| Laptop endpoint config | address literal | A hostname would need an unproxied DNS record, publishing the origin address (FR-005) |
| Origin peer config | **no `Endpoint` line** | The origin learns the laptop's current address from each handshake — this is what makes relocation work |
| Tunnel addresses | origin `10.10.0.1`, laptop `10.10.0.2` | Stable regardless of physical location |

## C1a — Transport-listener clarification (2026-09-06)

This contract selects **Option A** for the meaning of “no inbound.” The origin may listen on the WireGuard UDP transport port because the laptop is the outbound initiator and the origin is the responder. That listener is a private-link transport endpoint, not a public application or management entry point.

The origin firewall MUST allow only the approved origin address, the WireGuard UDP port, and the WireGuard transport/service. WireGuard peer public-key authentication is the peer admission control; the remote source cannot be narrowed to a fixed CIDR because the laptop changes networks. No TCP application port, management port, router port forward, or catch-all rule may be added for this link. The WireGuard peer configuration MUST continue to permit only `10.10.0.2/32` on the origin and `10.10.0.1/32` on the laptop. Packets accepted by the transport MUST be routable only to the laptop-side job-service binding; Feature 001, ComfyUI, administration, storage, metrics, and the origin pass-through remain unreachable directly from the Internet.

The origin's transport listener being reachable at the approved address does not contradict the outbound public-entry requirement: public application traffic still arrives through the provider edge and outbound connector, while the transport listener carries only the authenticated origin-to-laptop binding.

### C1a-1 — The boundary is feature-003 work, and it is verifiable (SC-018)

Feature 002's origin inbound surface was its hardened `:443` listener; the WireGuard posture rode along behind it and was never independently tested. Option A deletes that listener, which makes this UDP port the origin's **only** Internet-reachable socket. It is therefore specified, verified, and evidenced here rather than inherited.

| # | Rule | Must be true |
|---|---|---|
| 1 | Bound address | The approved origin address only |
| 2 | Port | Exactly one, explicitly named WireGuard UDP port |
| 3 | Service | The WireGuard transport/service only |
| 4 | Peer admission | Registered WireGuard peer public key; the remote source address cannot be pinned because the laptop moves (C1b) |
| 5 | Tunnel scope | `10.10.0.2/32` on the origin, `10.10.0.1/32` on the laptop — see C2 |
| 6 | TCP application listener | **None** |
| 7 | SSH / RDP / VNC / other management listener | **None** |
| 8 | Catch-all inbound rule | **None** |
| 9 | Router port forwarding | **None** |
| 10 | Direct GPU-laptop Internet exposure | **None** — see C7 |

**Verification obligations.** A static verifier reads the declared boundary and reports each rule above. It must **fail closed** on any rule it cannot evaluate rather than reporting a pass by omission. A negative test is mandatory: fixtures that add an unrelated inbound listener, widen the peer scope beyond `/32`, add a catch-all rule, or introduce a router port forward must all be **rejected**. Without it a verifier that merely confirms the expected rules exist would also pass a configuration that has those rules *plus* a violation. Live origin-local evidence that the running configuration matches this declaration is separate and remains blocked until authorized origin access exists.

## C1b — Mobility is a contract obligation (FR-040, SC-017)

The laptop is expected to change networks — university Wi-Fi, home network, mobile hotspot — and to re-establish this link on its own. That mobility is the reason the origin is the responder and the reason C1 forbids an `Endpoint` line on the origin peer: the laptop's current address is learned from each handshake instead of being configured.

| Must NOT change when the laptop moves | Why |
|---|---|
| Public DNS record | The record points at the provider edge, never at either machine (FR-005, FR-011b) |
| Public hostname | Naming continuity (FR-011) |
| Provider tunnel route | The route targets the tunnel, not a network location |
| Approved-origin configuration | The origin never learns where the laptop is from configuration |
| Feature 001 application configuration | The application is loopback-bound and location-independent (C4) |
| WireGuard tunnel addressing | `10.10.0.1` / `10.10.0.2` are stable by design (C1) |

Editing any of those six to restore connectivity after a move is a **failure** of FR-040, not a workaround for it. Acceptance requires at least two distinct external networks (SC-017).

## C1c — Option A is conditional on direct UDP reachability (FR-041)

Everything above assumes the approved origin actually receives the selected WireGuard UDP transport on its approved network path. Nothing in the repository proves that: the only origin-facing observation on record is a remote TCP probe that could not distinguish an unconfigured listener from a blocked path, and no UDP observation exists.

| Inspection result | Consequence |
|---|---|
| Origin receives the WireGuard UDP transport directly, no router forwarding | Option A is feasible; proceed |
| Origin cannot receive it without router port forwarding | **Option A is not feasible for this target.** Production stays blocked and the compute-link transport is redesigned on a separate outbound-initiated or NAT-traversing arrangement |

Forbidden as a fallback in the failing case: router port forwarding (FR-003), a public application port (FR-004), a public listener on the GPU laptop (FR-004, C7), and a paid relay or VPS (FR-007, FR-008). Until inspection resolves this the status is `PENDING TARGET INSPECTION` and must not be recorded as satisfied.

## C2 — Scope restriction (unchanged)

| Side | Peer scope | Forbidden |
|---|---|---|
| Laptop | `10.10.0.1/32` | `0.0.0.0/0` — would route the laptop's entire Internet through the origin |
| Origin | `10.10.0.2/32` | Any wider range |

Constitution III requires an internal binding's address scope to stay "as narrow as the specific peer it connects."

## C3 — Persistence (unchanged)

| Property | Value |
|---|---|
| Keepalive | Laptop side only — the side behind NAT |
| Reconnect | Automatic after network loss, network change, and reboot, with no operator command |

Without keepalive the NAT mapping expires while idle and the origin cannot reach back. The symptom is the service working initially, then falling to the unavailable notice minutes later with no error anywhere.

## C4 — Startup ordering — **CHANGED**

> **This section reverses feature 002.** Under feature 002 the laptop's web entry bound the tunnel address, so the tunnel had to come up first. Under feature 003 that listener is not the public entry, and gating on it breaks LAN-only operation (FR-037).

**Required arrangement:**

```text
Laptop boot
  ├─ feature 001 application starts immediately on loopback
  │    Next.js 127.0.0.1:3000 · FastAPI 127.0.0.1:8000 · ComfyUI 127.0.0.1:8188
  │    LAN reachable through the existing host port forward     ✅ independent of the binding
  │
  └─ WireGuard starts in parallel, retried with bounded backoff
       when it comes up → origin reaches 10.10.0.2 → host port forward → 127.0.0.1:3000
       public path restored                                      ✅ without restarting the app
```

| Rule | Requirement |
|---|---|
| No feature 001 service binds the private address exclusively | FR-023d |
| Binding availability must not gate application startup | FR-023a |
| Binding retry is asynchronous with bounded backoff | FR-023d |
| Public path resumes without restarting the application | SC-006e |
| LAN workflow fully usable with origin down and binding absent | SC-006d |

**Concrete changes required:**

| Artifact | Current state | Required state |
|---|---|---|
| `deploy/windows/services/web.xml` | binds `10.10.0.2`; `<depend>WireGuardTunnel$upstream</depend>` | binds loopback; WireGuard dependency removed |
| `scripts/windows/start_web_service.ps1` | polls for tunnel address and live handshake before starting | starts unconditionally on loopback |
| `deploy/windows/services/api.xml` | loopback-bound | unchanged — verify only |
| `deploy/windows/services/comfyui.xml` | loopback-bound | unchanged — verify only |

**Why the old design existed**: a service dependency can report "started" before the interface address exists, so feature 002 added address polling to close a real race. That reasoning was correct for feature 002's topology. It is obsolete here, and the polling now creates the failure it was meant to prevent.

## C5 — Recovery

Diagnose the failing layer before acting on it (FR-024). Restart the failed layer first; do not restart unrelated healthy layers. A dependent layer may be restarted or reconnected **only** when health evidence shows it did not recover on its own after the failed dependency returned.

```text
every interval:
  ├─ handshake stale                  → restart the binding; leave the application alone
  ├─ handshake live, app not serving  → restart only the failing application layer
  ├─ dependency returned but dependent still unhealthy after grace
  │                                   → reconnect or restart that dependent layer
  └─ 3 consecutive failures at one layer → stop looping, record diagnostic, surface the layer
```

The grace period exists because a dependent process may hold a stale connection after its dependency returns. Restarting it immediately would violate "avoid restarting unrelated healthy layers"; never restarting it would leave a permanently wedged connection.

## C6 — Terminology

Feature 002 called the laptop-side listener a "web entry." Under feature 003 that name belongs to the origin's public HTTP entry point. **The laptop-side role is the job service.** Where feature 002 documents a laptop-bound web entry, read job service.

## C7 — Boundary

| From | To | Allowed |
|---|---|---|
| Internet | GPU laptop | **Never** (FR-004); the only Internet-reachable origin socket is the authenticated WireGuard transport, which is not a direct laptop application path |
| Approved origin | GPU laptop | Only over this binding |
| Trusted LAN | GPU laptop | **Yes** — feature 001's existing LAN bindings are retained (FR-037) |

The GPU laptop must be unreachable from the Internet. It is **not** isolated from the LAN — feature 001 is a LAN service and that capability must survive. Planning confirmed the current mechanism is a host-level port forward from the LAN address to loopback.
