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
| Internet | GPU laptop | **Never** (FR-004) |
| Approved origin | GPU laptop | Only over this binding |
| Trusted LAN | GPU laptop | **Yes** — feature 001's existing LAN bindings are retained (FR-037) |

The GPU laptop must be unreachable from the Internet. It is **not** isolated from the LAN — feature 001 is a LAN service and that capability must survive. Planning confirmed the current mechanism is a host-level port forward from the LAN address to loopback.
