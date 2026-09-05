# Phase 11 Owner Gate — Updated for Cloudflare Public Entry

**Date:** 2026-09-05
**Feature:** `002-cloudflare-public-entry` (updates the gate inherited from
`001-local-3d-generation`)
**Task:** T005
**Verdict:** `BLOCKED — deployment evidence still pending`

This record captures the owner decisions for the new public-entry topology.
It does not claim that live DNS, certificates, firewall rules, or public
traffic have been changed. Network addresses in this evidence artifact are
masked per FR-026; exact values belong only in approved contracts or host-local
configuration.

## Requested architecture

The requested public entry is a Cloudflare-proxied subdomain. The
university-allocated origin address is retained as the origin
(`161.200.90.xxx`, masked here). The GPU laptop remains a separate mobile
compute node and connects outbound to the origin through the private WireGuard
link; moving the laptop must not require DNS or public proxy changes.

Cloudflare terminates visitor TLS and connects to the origin using an Origin CA
certificate with Full (strict) validation. The origin must require and verify
the provider client certificate and must reject direct traffic that did not
arrive through the provider. The application remains unchanged.

The alternate allocated address is out of scope and must never be configured,
forwarded, or probed. It is not reproduced here so this evidence remains
address-masked.

## Decisions recorded on 2026-09-05

| Decision | Status | Evidence / constraint |
|---|---|---|
| Public-entry mode | **APPROVED** | Cloudflare proxy in front of the allocated origin; the origin remains the real production origin. |
| Domain and provider account ownership | **PENDING — owner evidence required** | No hostname or Cloudflare account identity was supplied in the current workspace; do not infer personal ownership. |
| Public access policy | **PENDING — owner approval record required for exposure** | Repository configuration preserves no site-wide login and per-job capability tokens, but final public exposure requires an explicit owner decision and the v1.2.0 residual-exposure conditions. |
| Permitted users, territory, and model license | **PENDING — owner gate unresolved** | No verified model-license or permitted-territory approval is present. Do not expose the service publicly until the owner records the applicable decision. |
| Origin address assignment and live reachability | **PENDING-CUTOVER** | The allocation memo is the basis for the approved address, but the origin must be freshly checked to hold it and be externally reachable before deployment. |
| Origin OS and port 443 listener | **PENDING** | Must be confirmed on the origin; the current workstation is the mobile GPU laptop, not the origin. |
| Origin management path | **PENDING — T008** | Management port, trusted source range, and access proof must be recorded before default-deny is applied. |
| Border-firewall permission set | **APPROVED — T007** | The project lead explicitly approved exactly `443/tcp` from the provider's published ranges and `51820/udp` from any source; `network-permissions.md` records the approval. This is authorization only; live application and verification remain pending. Port `80/tcp` is explicitly not requested. |

## Re-scoped former router-forwarding gate

There is no home or office router in this topology. The old “router 80/443
forwarding” question is replaced by the university border-firewall permission
set defined in
[`contracts/port-policy.md`](../../specs/002-cloudflare-public-entry/contracts/port-policy.md):

- `443/tcp` inbound to the masked approved origin, restricted to the provider
  ranges.
- `51820/udp` inbound to the masked approved origin from any source, with
  WireGuard public-key authentication providing peer admission.
- `80/tcp` is not opened; all other non-management ports remain denied.

The written confirmation is retained in
[`network-permissions.md`](network-permissions.md). Discovering another
required inbound permission during cutover is a planning defect under FR-030.

## Safety boundary

- Repository configuration is preparation only; no public infrastructure was
  changed while this gate was updated.
- No certificate was requested or accepted.
- No DNS record or firewall rule was changed.
- No real private key, API token, password, or job token is stored in this
  evidence file.
- The gate remains blocked until the pending operator inputs, management-path
  proof, and later external acceptance evidence are complete.
