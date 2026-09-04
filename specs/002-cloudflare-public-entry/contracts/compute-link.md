# Contract: Compute Link (Origin ↔ GPU Laptop)

**Feature**: `002-cloudflare-public-entry` | **Date**: 2026-09-05

The link that lets the fixed origin reach a laptop whose location and public address change. Carried forward unchanged from the superseded planning round — the Cloudflare layer sits above this and does not alter it.

---

## L1 — Direction and addressing

| Property | Value | Why it must be this way |
|---|---|---|
| Initiator | **The laptop**, outbound | The laptop must need no inbound reachability on any network it joins (FR-016) |
| Responder | The origin, `51820/udp` | The origin has a stable public address; the laptop does not |
| Laptop endpoint config | `161.200.90.4:51820` — **address literal** | A hostname would need an unproxied DNS record, which publishes the origin address and defeats FR-001b (R5) |
| Origin peer config | **No `Endpoint` line** | The origin learns the laptop's current address from each handshake. This is the mechanism that makes relocation work |
| Tunnel addresses | origin `10.10.0.1`, laptop `10.10.0.2` | Stable regardless of physical location — what the proxy configuration targets |

## L2 — Scope restriction

| Side | Peer scope | Forbidden |
|---|---|---|
| Laptop | `10.10.0.1/32` | `0.0.0.0/0` — would route the laptop's entire Internet through the origin |
| Origin | `10.10.0.2/32` | Any wider range |

A full-tunnel default route on the laptop would send unrelated personal traffic across the university network, waste origin bandwidth, and exceed what the constitution permits for an internal binding, which must stay "as narrow as the specific peer it connects".

## L3 — Persistence

| Property | Value |
|---|---|
| Keepalive | Set on the **laptop side only** — the side behind NAT |
| Reconnect | Automatic after network loss, network change, and reboot, with no operator command |

Without keepalive, the NAT mapping expires during idle periods and the origin can no longer reach back. The symptom is the service working initially and then falling to the unavailability notice some minutes later, with no error anywhere — a failure that is disproportionately hard to diagnose after the fact.

## L4 — Startup ordering

The laptop's web entry binds to the tunnel address, which does not exist until the tunnel is up. Starting it first fails the bind.

```
Network ready
  → tunnel service started
  → tunnel address present AND handshake live
  → engine → backend → web entry (binds 10.10.0.2:3000)
```

A service dependency alone is **not sufficient**: a dependency can report "started" before the interface address actually exists. The startup wrapper must additionally poll for both the address and a live handshake before starting the web entry, and exit non-zero on timeout so the service manager retries.

This is the defect class that makes reboot tests fail intermittently rather than consistently, which is why acceptance requires **at least three consecutive** reboot trials (SC-003) rather than one.

## L5 — Recovery

Diagnose the failing layer before acting on it.

```
every interval:
  ├─ handshake stale          → restart the tunnel; do not touch the web entry
  ├─ handshake live, web entry not listening
  │                           → restart the web entry only
  └─ both healthy             → do nothing
```

Constraints:

- Cooldown between attempts at the same layer.
- Stop and escalate after a bounded number of unsuccessful attempts. A condition automated recovery cannot fix — a network that blocks outbound UDP, for instance — must stay visible rather than being buried in restart noise.
- Log which layer was chosen and why.

Restarting the web entry in response to a dead tunnel cannot succeed and will loop indefinitely.

## L6 — Fallbacks for networks that block outbound UDP

Hotel, guest, and some corporate networks block outbound UDP. Prepare these before they are needed rather than discovering the limitation during a demonstration:

1. WireGuard on `443/udp` — many networks pass it without inspecting protocol.
2. SSH reverse tunnel over TCP — traverses almost anything; requires a second inbound permission at the origin.
3. Mesh VPN with provider relays — removes the inbound UDP requirement entirely, at the cost of a second third party in the path. This is also the escalation path if network staff refuse the UDP permission outright.

## L7 — Verification

| Check | Type | Proves |
|---|---|---|
| Unauthenticated UDP to `51820` gets no response | Negative | Unauthenticated packets are dropped silently |
| Real peer completes a handshake, handshake timestamp is fresh, origin reaches `10.10.0.2:3000` | **Positive** | **The UDP permission actually traverses the border firewall** |
| Laptop's physical address is not `10.10.0.2` during the test | Sanity | The test is exercising the tunnel, not a local shortcut |

The positive test is the one that matters. A silent port and a blocked port are indistinguishable from outside, so a negative result alone cannot tell "WireGuard is working correctly" apart from "network staff never opened the port" (FR-028).
