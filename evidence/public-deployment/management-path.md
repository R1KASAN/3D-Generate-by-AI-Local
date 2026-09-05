# Origin Management Path — Phase 2 Gate

**Feature:** `002-cloudflare-public-entry`
**Task:** T008
**Status:** **DECIDED — live origin proof pending**
**Recorded:** 2026-09-05

The project has selected SSH over TCP 22, reached from a University VPN or
bastion public egress address restricted to a narrow `/32`, with a physical or
VM console as fallback. The current workspace is the mobile GPU laptop, not the
origin that holds the approved public address, so the exact egress CIDR, origin
listener, and access proof cannot be established from here.

## Required decision and proof

| Item | Required value | Current status |
|---|---|---|
| Management service | SSH | **DECIDED — listener proof pending** |
| Management TCP port | TCP 22 | **DECIDED — active listener proof pending** |
| Trusted source range | University VPN or bastion public egress `/32` | **DECIDED — exact CIDR pending** |
| Fallback access | Physical or VM console | **DECIDED — availability proof pending** |
| Access proof | Fresh connection from that source while the origin is still open | `PENDING` |
| Firewall state | No default-deny change applied | **Confirmed from this workspace; no origin change was made** |

## Where to obtain the missing values

These are origin and network-owner inputs; they cannot be derived from the GPU
laptop or Cloudflare configuration.

- **Management service and port:** ask the Edge/origin administrator which
  owner-approved service will remain available, then confirm that it is
  listening on the origin. For Linux, inspect `ss -lntp` and the SSH service;
  for Windows, inspect `Get-NetTCPConnection -State Listen` and the approved
  remote-management service. Do not choose a port merely because it is common.
- **Trusted source CIDR:** obtain the source range from the network path you
  will actually use: an institutional VPN, a bastion/jump host, or a fixed
  administration address. Prefer one `/32` or the narrow VPN CIDR. Never use
  `Any`, and do not use a changing home/ISP address unless its stability and
  ownership are documented.
- **Access proof:** from that exact source network, make a real authenticated
  connection while the origin is still open. Windows operators can use
  `Test-NetConnection <origin> -Port <port>` followed by the approved client;
  Linux operators can use `nc -vz <origin> <port>` followed by SSH or the
  approved client. The reachability probe alone is not sufficient evidence.

The Edge owner/IT administrator is the authoritative source for the listener
and service choice. The border-firewall/network administrator is the
authoritative source for whether the selected source CIDR is permitted. Record
only the masked service, port, source description/CIDR, timestamp, and success
of the fresh connection; never record credentials or private keys.

## Closure procedure

On the origin, before applying any default-deny rule:

1. Select the management service, TCP port, and narrow trusted source range.
2. Confirm the service is listening on the origin.
3. Open a new connection from the approved source and record a successful
   authenticated access, without recording credentials or private addresses.
4. Record the masked port/source description and timestamp here.
5. Keep the session open until a second connection succeeds after the firewall
   boundary is applied.

Until these steps are completed, T008 is not complete and the public-edge
firewall must not be applied.
