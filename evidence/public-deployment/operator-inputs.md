## Feature 003 access correction — 2026-09-06

**MANUAL/BLOCKED.** The operator confirms no remote connection method, confirmed SSH/RDP/management service, or saved origin host configuration is available. Only the approved public address is known (masked: `161.200.90.x`). Do not probe or assume a public management port. Physical or authorized remote access must precede origin inspection/configuration/trials. Origin OS, interface ownership, egress and source-address bindability remain unverified. The hostname candidate is `twin3dgen.mangosgo.com`; written owner consent and route creation remain pending. Older inbound-port and management assumptions below are historical, not observed permissions or current instructions.

## Feature 003 target-inspection register — 2026-09-06 (Option A remediation)

`PENDING TARGET INSPECTION` below means the design decision is made and only physical or live evidence is missing. It is **not** an unresolved architecture question and must never be read as an approval.

| Item | Status | Closed by |
|---|---|---|
| Origin operating system and version | `PENDING TARGET INSPECTION` | tasks.md T065 |
| Origin's actual outbound egress address | `PENDING TARGET INSPECTION` | tasks.md T065 |
| Whether the approved address is directly bindable on the origin | `PENDING TARGET INSPECTION` | tasks.md T066 |
| Whether the running origin firewall and WireGuard configuration match the C1a transport boundary | `PENDING TARGET INSPECTION` | tasks.md T066a (SC-018) |
| Whether the origin **directly receives** the WireGuard UDP transport without router port forwarding | `PENDING TARGET INSPECTION` | tasks.md T066b (FR-041). **A negative result voids Option A** |
| Whether the approved address still sits on a machine separate from the GPU | `PENDING TARGET INSPECTION` | tasks.md T065 (FR-013 re-evidencing trigger) |

**Superseded by feature 003, retained below only as history:** the "approved design requires inbound `443/tcp`" constraint (feature 003 has no Internet-facing application or management listener) and the `TCP 22 (SSH)` management-port row (feature 003's Out of Scope forbids public SSH, RDP, and VNC, and SC-018 requires no management listener on the origin at all). Neither is a current instruction or an observed permission. The one inbound socket feature 003 permits is the narrowly scoped WireGuard UDP transport listener defined by the Option A compute-link contract (C1a).

# Operator Inputs — Cloudflare Public Entry

**Feature:** `002-cloudflare-public-entry`
**Recorded:** 2026-09-05
**Purpose:** Phase 1 capture of the inputs required before any public cutover.

This file is an evidence artifact. Network addresses are masked and no
credentials, tokens, or passwords are recorded. `PENDING` means the value must
be confirmed by the operator on the origin before cutover; it is not an
assumption or an approval.

## Input record

| Required input | Recorded value | Status / evidence |
|---|---|---|
| Origin operating system and version | `PENDING — origin host not present in this workspace` | The local machine inspected on 2026-09-05 is the GPU laptop, not the origin. Its observed OS was Windows 11 Home Single Language, version `10.0.26200`; this must not be treated as the origin OS. The operator has confirmed (2026-09-05) that a physical server exists at the Information and Communication Engineering Research Laboratory, 13th floor, Charoenwitwa Engineering Building, and is the intended origin machine — but its OS has not been inspected from this workspace. |
| Whether the origin holds the approved address | `OPERATOR-ASSERTED, not independently verified` | The operator states this is the one machine that will be used and that they hold rights to it per the memo reviewed in `allocation-memo-review.md`. That memo names a different project and an outbound-only purpose; see that file for the resulting owner risk-acceptance decision. Live IP assignment on that machine has not been inspected from this workspace. |
| Whether anything listens on origin port 443 | `PROBED, response negative` | A remote probe from the GPU laptop on 2026-09-05 (`allocation-memo-review.md`) found no response on TCP 443 or TCP 80 at `161.200.90.4`, and no ICMP response. This does not distinguish an unconfigured listener from a blocked path, and is not authoritative for the clarified design: no inbound application or management listener is allowed, while the C1a WireGuard UDP transport listener may exist and requires origin-local inspection. |
| Registered public domain | `PENDING — owner must supply the hostname` | The design requires one personally controlled hostname; no domain name was supplied in the repository or current task context. Do not substitute an IP address. |
| Intended origin management port | `TCP 22 (SSH)` | Owner decision recorded; the firewall contract intentionally provides no default, and the port must still have a working listener before default-deny is applied. |
| Intended management source range | University VPN or bastion public egress CIDR (`/32`) | Path decision recorded; the exact CIDR must still be confirmed from the selected VPN/bastion and must never be `Any`. |

## Known constraints already recorded

- The approved design requires inbound `443/tcp` from the provider's published
  ranges and `51820/udp` from any source for the authenticated WireGuard peer.
- Port `80/tcp` is not required and must remain closed.
- The GPU laptop is a separate mobile machine; its local listener inventory is
  not evidence about the origin.
- No public deployment, certificate request, DNS change, or firewall change
  was performed while recording this file.

## Closure checks before cutover

The operator must update the pending rows with fresh, masked observations from
the origin and retain the unmasked values only in the origin's protected local
configuration. Before applying a firewall boundary, verify the selected
management service is reachable from the approved source and that the origin
actually owns the approved address. No cutover task may treat this file as
fully approved while a row remains `PENDING`.
