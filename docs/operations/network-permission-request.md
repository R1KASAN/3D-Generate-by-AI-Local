# HISTORICAL — no feature-004 network change

Feature 004 requires outbound cloudflared only. Do not apply the inbound
permissions described below to the single Notebook architecture.

# Network Permission Request — Cloudflare Public Entry

**Feature:** `002-cloudflare-public-entry`
**Status:** Request definition — not a firewall change

Please approve exactly the following inbound permissions for the university
border firewall, targeting the single approved origin address recorded in the
project contracts:

| Port | Protocol | Source | Purpose |
|---|---|---|---|
| 443 | TCP | Cloudflare's currently published address ranges | Proxied HTTPS traffic to the origin |
| 51820 | UDP | Any source | Outbound-initiated WireGuard compute link; peer admission is by WireGuard public-key authentication |

## Explicit exclusions

- **Do not open port 80/tcp.** The origin uses Cloudflare Origin CA, which does
  not require an inbound validation path, and HTTP-to-HTTPS redirection occurs
  at the provider edge.
- Do not open ports 3000, 8000, 8188, 3389, 2019, or any other application,
  engine, or administration port through this request.
- Do not create a DNS record for the tunnel endpoint. The laptop uses the
  origin address as a literal so the origin is not disclosed by DNS.

Management access is a separate, owner-approved path. Its port and trusted
source range must be selected and proven in
`evidence/public-deployment/management-path.md` before the origin default-deny
boundary is applied; it is intentionally not guessed or added to this exact
two-permission request.

## Allocation basis

The request applies to the address named in an Electrical Engineering
Department memo dated 26 ธ.ค. 2567, Chulalongkorn University (no reference
number is present in the source document). That memo requests an
authentication exemption for a different, named research project; see
`evidence/public-deployment/allocation-memo-review.md` for what it actually
states and for the operator's recorded decision to use the address here
regardless. The evidence record in
`evidence/public-deployment/network-permissions.md` defines these two requested
inbound permissions for this feature and records the project-lead approval;
live firewall application remains pending until the management path and origin
are ready.

## Change-control requirement

The recorded approval must be applied and verified before cutover. If any
further inbound permission is discovered during deployment, stop and treat it
as a planning defect under FR-030; do not quietly broaden this request.
