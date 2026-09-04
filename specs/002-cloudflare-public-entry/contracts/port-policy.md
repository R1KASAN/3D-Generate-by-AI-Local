# Contract: Inbound Port Policy

**Feature**: `002-cloudflare-public-entry` | **Date**: 2026-09-05
**Status**: AUTHORITATIVE

> This table is the single source of truth for inbound network permissions.
> Every firewall implementation — the PowerShell one, and an nftables one if the
> origin turns out to run Linux — derives from this table. Verifiers assert
> against this table, not against a hard-coded rule list. If an implementation
> and this table disagree, **the table is correct and the implementation is a bug**.
>
> Rationale: R7. Two implementations that each carry their own port list will
> drift, which Constitution Principle VII exists to prevent.

---

## Origin `161.200.90.4` — inbound

| Port | Proto | Source scope | Purpose | Required? |
|---|---|---|---|---|
| 443 | TCP | **Cloudflare published ranges only** | Proxied application traffic | Yes |
| 51820 | UDP | **Any** | WireGuard compute link | Yes — see note 2 |
| *management* | TCP | **Approved management source only** | Administration of the origin itself | Yes — see note 3 |
| **80** | TCP | — | — | **NO — must not be opened** (note 1) |
| 3000, 8000, 8188, 3389, 2019 | TCP | — | — | **NO — explicit block rules** |
| everything else | — | — | — | **DENY** (default-deny profile) |

### Note 1 — why port 80 is absent

Both of its former consumers are gone. Certificate issuance no longer touches the origin (Origin CA needs no inbound validation, R1), and HTTP-to-HTTPS redirection now happens at the provider edge before any request reaches the origin. Opening it would be an inbound permission with no consumer.

**This is a change from the superseded design.** `configure-public-edge.ps1` currently has an `-EnableHttp` parameter defaulting to `$true` and creates a rule named `Local3D Edge HTTP (ACME/redirect)`. Both must be removed, and the verifier must assert the rule's **absence**.

### Note 2 — why 51820/udp is open to `Any`, and why that is not a hole

The laptop's public source address changes every time it moves networks. An allowlist would defeat the mobility requirement that motivates the entire design. Security is WireGuard's per-packet public-key authentication: a packet not signed by the registered peer key is dropped silently, with no response at all — a scanner cannot distinguish this port from a filtered one.

**This permission survives the Cloudflare change.** The proxy layer removes port 80, not 51820. It must appear in the request to network staff (FR-030); it was the permission the superseded planning round discovered late.

### Note 3 — management port

No default is provided deliberately. The port and its source range are operator inputs (R7), and guessing wrong locks the operator out of the origin permanently once default-deny is applied. The configuration script must require both explicitly and must refuse to run until a listener is already present on the chosen port.

---

## GPU laptop — inbound

| Port | Proto | Interface | Source scope | Purpose |
|---|---|---|---|---|
| 3000 | TCP | **WireGuard only** | `10.10.0.1/32` | Web entry, reachable from the origin only |
| 8000 | TCP | loopback | — | Backend — no inbound rule |
| 8188 | TCP | loopback | — | Engine — no inbound rule, never reachable from the origin |
| 3389 | TCP | — | — | **DENY unconditionally** |
| everything else | — | physical NICs | — | **DENY** |

## GPU laptop — outbound

| Destination | Proto | Purpose |
|---|---|---|
| `161.200.90.4:51820` | UDP | Compute link, initiated from the laptop |

---

## Request to university network staff

Exactly two inbound permissions are required at `161.200.90.4`, plus whatever the management path needs:

```
443/tcp   inbound — restricted to Cloudflare published address ranges
51820/udp inbound — from any source (peer authentication is by public key)
```

Port 80 is **not** requested. All other ports should remain closed.

Per FR-030, this list must be confirmed **in writing before cutover begins**. Discovering a further required permission during cutover is a planning defect, not a routine follow-up.

---

## Provider-range maintenance

Cloudflare's published address ranges change. The 443 rule must be regenerated from the current published list rather than from a copy pasted once.

- `deploy/firewall/cloudflare-ranges.ps1` fetches the current list and rebuilds the rule.
- It **must fail closed**: if the list cannot be retrieved, leave the existing rule in place and exit non-zero. It must never fall back to `Any`.
- A stale list causes refused legitimate traffic — a visible outage. That is the correct failure direction (R3), and the reason mTLS rather than the allowlist is the primary control.
