# WireGuard Transport Boundary Evidence (T058b)

- Date/time (UTC): 2026-09-05T22:20:43.125899+00:00
- Declaration source: deploy\wireguard\origin-transport-boundary.md
- Credentials, capability tokens, and full public IP addresses are omitted.

| Check | Observed | Expected | Verdict |
|---|---|---|---|
| address | 161.200.90.x | 161.200.90.x | **PASS** |
| protocol | udp | udp | **PASS** |
| port | 51820 | 51820 | **PASS** |
| service | wireguard | wireguard only | **PASS** |
| peer_admission | public_key | public_key | **PASS** |
| origin_allowed_ips | 10.10.0.x/32 | 10.10.0.x/32 | **PASS** |
| laptop_allowed_ips | 10.10.0.x/32 | 10.10.0.x/32 | **PASS** |
| tcp_application_listener | none | none | **PASS** |
| management_listener | none | none | **PASS** |
| catch_all_inbound_rule | none | none | **PASS** |
| router_port_forwarding | none | none | **PASS** |
| gpu_laptop_internet_exposure | none | none | **PASS** |

- Validates the declared boundary against contracts/compute-link.md C1a-1 (SC-018). This is not live-origin evidence; that is tasks.md T066a.
- Overall verdict: **PASS**
