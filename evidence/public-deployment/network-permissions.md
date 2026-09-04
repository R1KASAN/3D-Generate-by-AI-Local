# Network Permission Confirmation — `002-cloudflare-public-entry`

**Task**: T007 | **Date recorded**: 2026-09-05

## Requested permissions

| Port | Protocol | Source | Purpose |
|---|---|---|---|
| 443 | TCP | Cloudflare published address ranges | Proxied HTTPS to origin |
| 51820 | UDP | Any | WireGuard compute link (origin ↔ GPU laptop) |

Port 80 is explicitly **not** requested (see `contracts/port-policy.md` note 1 — Cloudflare Origin CA needs no inbound validation path, so no ACME/redirect port is needed at the origin).

Origin address: `161.200.90.4` only. `161.200.90.3` is out of scope for this permission and MUST NOT be affected by any change made under it.

## Authorization record

- **Authorizing role**: Head of IT (หัวหน้าสาย IT), self-attested by the operator recording this file.
- **Basis**: Operator holds network/firewall authority for the university border network described in this document, and was directed to complete this project (deployment of `002-cloudflare-public-entry`) as part of that role.
- **Relationship to prior approval**: This is a distinct authorization from memo วฟ.2174/2567 (26 ธ.ค. 2567), which covers IP allocation (`161.200.90.3`, `161.200.90.4`) and the authentication exemption only. That memo does not itself authorize opening 443/tcp or 51820/udp; this record is the authorization for those two specific permissions, made under the operator's own IT authority and citing the memo as the basis for which project and which address it applies to.
- **Verbal confirmation**: Also separately obtained from ศ.ดร.ลัญฉกร วุฒิสิทธิกุลกิจ (signatory of the original memo, confirmed to hold authority to direct this firewall change). Recorded here as supporting context; the operative authorization for this specific permission is the operator's own IT role above.

## Status

**CONFIRMED** — T007 is satisfied by this record. No further external written confirmation is required, because the operator holds the authorizing role directly rather than requesting it from a separate party.

## Outstanding

Per FR-030, if any further inbound permission beyond the two listed above is discovered to be necessary during cutover, that is a planning defect and must be added here with the same authorization record before being applied — not treated as a routine follow-up.
