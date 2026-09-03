# Approved LAN Entry Evidence (Phase 10)

- Date/time (UTC): 2026-09-03T16:39:01.8665248Z
- Server LAN address: `172.20.10.6` (current address at configuration time)
- Approved entry: `http://172.20.10.6:3000/`
- Scope: current RFC1918 local subnet only; no Internet/router forwarding.

| Check | Observed | Verdict |
|---|---|---|
| Port forwarding | `172.20.10.6:3000 -> 127.0.0.1:3000` | **PASS** |
| Firewall scope | inbound TCP 3000, local address `172.20.10.6`, remote `LocalSubnet` | **PASS** |
| API boundary | `8000` has no non-loopback listener | **PASS** |
| ComfyUI boundary | `8188` has no non-loopback listener | **PASS** |
| Local entry verification | `verify_lan_boundary.ps1` returned PASS | **PASS** |

This file proves only the server-side entry configuration. T082/T083 still
require execution from a separate physical LAN client.
