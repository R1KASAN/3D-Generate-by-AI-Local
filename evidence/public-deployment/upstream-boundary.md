# GPU upstream-boundary evidence

**Feature:** `002-cloudflare-public-entry`  
**Tasks:** T051, T052, T054  
**Status:** BLOCKED — applying and proving the laptop firewall requires the
target Windows NVIDIA laptop and a second host on its physical network.

## Read-only current-state observation

On 2026-09-05 the local target was inspected without changing network state:

- The required WireGuard adapter and tunnel address were not present.
- The web service was not listening on the required tunnel address.
- Two existing LAN `portproxy` entries were present, so the upstream boundary
  precondition is not satisfied.

These observations reinforce the block. The entries were not removed during
this run because doing so changes live connectivity and requires an
owner-approved rollback path; the configured boundary script will refuse to
run while any portproxy entry remains.

## Required policy

- The web-entry port is reachable only from the edge peer's tunnel address.
- Backend, ComfyUI, and remote-administration ports are blocked from the
  physical LAN and other untrusted interfaces.
- The LAN-lockdown probe must be run from a second device, including once from
  a network the laptop does not own, and must record refusal without exposing
  addresses or credentials.

## Closure sequence

1. On the target laptop, run the owner-approved upstream-boundary configure
   script with the edge peer address.
2. From a new edge-side connection, run the read-only verifier and save its
   masked output here.
3. From a second physical-LAN device, run
   `scripts/verify/test_upstream_lan_lockdown.py` and append the masked result.

No live PASS is claimed in this template.
