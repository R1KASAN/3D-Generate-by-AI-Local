# Origin WireGuard Transport Boundary (SC-018)

**Feature**: `003-outbound-tunnel-entry` | **Tasks**: T058a | **Date**: 2026-09-06

Declares the **only** inbound socket Option A permits on the approved origin
(contracts/compute-link.md C1a, C1a-1). Feature 002's inbound surface was its
hardened `:443` listener, and the WireGuard posture rode along behind it
untested. Option A removes that listener, which makes this UDP port the
origin's sole Internet-reachable socket — so this feature declares and
verifies it rather than inheriting an assumption.

This file is the **declared intent**, checked statically by
`scripts/verify/test_wireguard_transport_boundary.py` (T058b) and by
`tests/security/test_wireguard_transport_boundary.py` (T056a/T056b). It is
**not** a record of the running configuration — that is origin-local
evidence, separate and still `PENDING TARGET INSPECTION` (tasks.md T066a).

## Declared boundary

```boundary
address: 161.200.90.4
protocol: udp
port: 51820
service: wireguard
peer_admission: public_key
origin_allowed_ips: 10.10.0.2/32
laptop_allowed_ips: 10.10.0.1/32
tcp_application_listener: none
management_listener: none
catch_all_inbound_rule: none
router_port_forwarding: none
gpu_laptop_internet_exposure: none
```

| Field | Declared value | C1a-1 rule |
|---|---|---|
| `address` | the approved origin address only | #1 |
| `protocol` / `port` | exactly one explicitly named WireGuard UDP port | #2 |
| `service` | the WireGuard transport/service only | #3 |
| `peer_admission` | registered WireGuard peer public key (the source address cannot be pinned — the laptop moves, C1b) | #4 |
| `origin_allowed_ips` / `laptop_allowed_ips` | `/32` tunnel scope on both sides | #5 |
| `tcp_application_listener` | **none** | #6 |
| `management_listener` | **none** (no SSH/RDP/VNC/other) | #7 |
| `catch_all_inbound_rule` | **none** | #8 |
| `router_port_forwarding` | **none** | #9 |
| `gpu_laptop_internet_exposure` | **none** (see contracts/compute-link.md C7) | #10 |

Any field that is missing, empty, or holds a value other than what the table
requires fails that field's check individually — the verifier reports each
rule by name rather than a single pass/fail (see T058b's fail-closed
behavior).

## Per-OS rule snippets (provisional)

The approved origin's operating system is unverified (`PENDING TARGET
INSPECTION`, research.md R1). The declaration above is OS-independent by
design; translating it into actual firewall rules is necessarily OS-specific
and stays provisional until physical inspection confirms the origin OS.
Provisional snippets live under `deploy/firewall/origin/` and are marked
unconfirmed — do not apply them without first confirming the origin OS
matches.

## What this file does not prove

- That the running origin firewall actually matches this declaration
  (tasks.md T066a, blocked on authorized origin access).
- That the origin can **directly receive** this UDP transport without
  router port forwarding (tasks.md T066b, FR-041). A negative result there
  voids Option A for this target regardless of what this file declares.
- Anything about application or management ports elsewhere on the origin —
  those are covered by `contracts/origin-entry.md` O2 and
  `scripts/verify/test_origin_lockdown.py`.
