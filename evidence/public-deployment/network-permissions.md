# Network Permission Confirmation — Cloudflare Public Entry

**Feature:** `002-cloudflare-public-entry`
**Task:** T007
**Date recorded:** 2026-09-05
**Status:** **APPROVED BY PROJECT LEAD — live application pending**

This artifact records the exact permission set explicitly approved by the
project lead in this task conversation. It does not claim that the rules have
been applied to the live border firewall. Network addresses are masked per
FR-026; the origin is the single approved project address
(`161.200.90.xxx`).

## Requested permission set

| Port | Protocol | Source | Purpose |
|---|---|---|---|
| 443 | TCP | Cloudflare published address ranges | Proxied HTTPS to the origin |
| 51820 | UDP | Any | WireGuard compute link; peer authentication is by public key |

Port `80/tcp` is explicitly **not** requested. All other non-management ports
remain denied. The management path is a separate gate and is not inferred from
this record.

## Approval record

- **Authorizing role:** Project lead; the user explicitly stated that they are
  the approving authority for this project and have approved T007.
- **Approval reference:** Explicit written approval in the task conversation,
  recorded 2026-09-05; no credentials or unmasked addresses are stored.
- **Approval scope:** Exactly both rows in the table above; port `80/tcp` is
  excluded and no additional inbound permission is implied.
- **Allocation basis:** The Electrical Engineering Department memo dated
  26 ธ.ค. 2567 (no reference number is present in the source document) names
  the allocated addresses. See
  [`allocation-memo-review.md`](allocation-memo-review.md) for what the
  document actually states, including that its named project and stated
  purpose differ from this project's, and for the operator's risk-acceptance
  decision to use the address here regardless. The alternate allocated
  address is out of scope and is not reproduced in this evidence.

**Required next action:** Apply and verify these exact rules only after T008
proves the management path and the live origin is ready. No additional inbound
permission may be added during cutover without a new approval; discovering one
would be a planning defect, not a routine follow-up request.
