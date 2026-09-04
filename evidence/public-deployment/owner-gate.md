# Phase 11 Owner Gate — BLOCKED

**Date:** 2026-09-04
**Feature:** `001-local-3d-generation`
**Task:** T085
**Verdict:** `BLOCKED`

Phase 11 cannot proceed to public traffic because required decisions below
remain unapproved in writing. Repository artifacts (Caddy config, WireGuard
templates, firewall scripts, tests) have been authored under Stage 1 of
`C:\Users\MetaHosP\.claude\plans\router-ai-eventual-tide.md` — this is
config-as-code preparation, not deployment. No public infrastructure has
been changed.

## Architecture (updated 2026-09-04)

Public IP `161.200.90.4` was assigned to this project by memo วฟ.2174/2567
(26 ธ.ค. 2567, ภาควิชาวิศวกรรมไฟฟ้า จุฬาลงกรณ์มหาวิทยาลัย), along with an
authentication exemption. **`161.200.90.3` is allocated separately and is
never to be configured, forwarded, or probed by anything in this
repository** — enforced in code by
`deploy/firewall/configure-public-edge.ps1` and
`tests/security/test_caddy_contract.py`.

The GPU compute node (this laptop, RTX 5070) is **not** the box that holds
`161.200.90.4`. It connects outbound to a fixed edge server over a
WireGuard tunnel (`10.10.0.2` ↔ `10.10.0.1`), which is what lets the
laptop move between the university, home, and mobile networks without any
DNS, firewall, or Caddy configuration change. See the plan above for full
rationale, the port policy table, and the mobility acceptance test.

## Required decisions

| Decision | Status | Required evidence |
|---|---|---|
| Model-license and permitted-user territory scope | BLOCKED | Written owner approval naming the permitted scope. Unaffected by the IP assignment; still outstanding. |
| Domain or DDNS provider/hostname | BLOCKED (narrowed) | DDNS is no longer relevant (the assignment is static). Still need the actual hostname owner will use — required for ACME (see `.env.example`'s note on the IP-certificate fallback if no hostname is available). |
| Public-entry policy | APPROVED | Owner confirmed 2026-09-04: no site-wide Caddy username/password; job resources remain protected by per-job tokens. Constitution amended to 1.1.0 (2026-09-04) to permit this policy explicitly. |
| DNS/DDNS account owner | BLOCKED | Written owner approval naming who controls the DNS zone/account (request ticket reference, not credentials). |
| Current Public IP revalidation | PENDING-CUTOVER | Cannot be marked APPROVED before the edge server actually holds and serves from `161.200.90.4` — the assignment memo is not itself current-state evidence (see `specs/001-local-3d-generation/quickstart.md`). To be closed with a freshly observed, masked value once Stage 3 of the plan runs. |
| Static/dynamic and CGNAT status | APPROVED (in principle) | The memo confirms a static, directly-assigned, non-CGNAT address. Evidence of the address being genuinely reachable with no NAT in front of it is still PENDING-CUTOVER, to be closed alongside the row above. |
| Router 80/443 forwarding capability | BLOCKED (re-scoped) | No home/office router exists in this topology — the address is assigned directly to a university-network edge server. The equivalent gate is: **the university border firewall permits inbound 443/tcp, 80/tcp, and 51820/udp (WireGuard) to 161.200.90.4**, and no other inbound port. Written confirmation from university IT is still required. |

## Safety boundary

- Caddy configuration has been authored in the repository
  (`deploy/caddy/Caddyfile`) but has not been deployed or exposed anywhere.
- WireGuard configuration templates have been authored
  (`deploy/wireguard/*.conf.example`) with no real keys committed.
- DNS/DDNS and any border-firewall rule have not been changed.
- Windows Firewall rules on either machine have not been applied from the
  new scripts (`deploy/firewall/configure-upstream-boundary.ps1`,
  `deploy/firewall/configure-public-edge.ps1`) — both require
  `-OwnerApproved` and fail closed on any precondition violation.
- No certificate has been requested or accepted.
- No public port has been opened.
- Ports 3000, 8000, 8188, and 3389 remain outside public reach in the
  approved design (3000 is reachable only via the WireGuard tunnel from
  the edge's tunnel address, never from the public internet or from the
  laptop's physical LAN).

T086–T092 remain pending until every blocked decision above is explicitly
approved in writing by the owner/operator, and until university IT
confirms the border-firewall port policy. The owner-approved access-control
policy is public HTTPS entry without a site-wide login plus per-job token
protection for status, preview, and download.
