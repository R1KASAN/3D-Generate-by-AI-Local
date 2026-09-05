> **RETIRED for feature 003 (2026-09-06).** The inbound-era rules below are historical and must not be applied to the outbound origin. `configure-public-edge.ps1` now stops before mutation. Use `docs/operations/tunnel-setup.md` and feature 003 contracts. Origin OS/access are unverified. No remote-management service or public management probe is authorized. The clarified contract permits only the separately scoped WireGuard UDP transport listener; it does not permit an inbound application or management listener and does not itself authorize a firewall change.

# Firewall Implementation Contract

The authoritative inbound network policy for this feature is
[`specs/002-cloudflare-public-entry/contracts/port-policy.md`](../../specs/002-cloudflare-public-entry/contracts/port-policy.md).
It governs every firewall implementation in this repository, including the
PowerShell edge script and any future Linux/nftables implementation.

The policy table is the single source of truth for required sources, ports,
protocols, and explicit blocks. An implementation must derive its rules from
that policy and its verifier must check the resulting state against it.

If a firewall implementation disagrees with the policy table, **the table is
correct and the implementation is an implementation bug**. Do not edit the
policy merely to make a script pass. Resolve the implementation defect or
raise a separately approved architecture change.

## Current boundary summary

- Origin HTTPS: `443/tcp`, restricted to the provider's published ranges.
- Compute link: `51820/udp`, open to any source because WireGuard authenticates
  the peer cryptographically and the mobile laptop's source address changes.
- Management: one explicitly chosen TCP port from one explicitly approved
  source range; there is no safe default.
- Port `80/tcp`: must not be opened.
- Backend, generation engine, web-entry, and remote-administration ports:
  denied according to the authoritative policy.

The public-edge configuration script must fail closed on missing owner approval,
missing administrator rights, an unassigned approved address, an unconfirmed
management listener, or a missing Caddy binary. Before ending an administrative
session after a firewall change, open a new connection and verify management
access.
