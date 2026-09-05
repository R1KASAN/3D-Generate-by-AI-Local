# Windows origin transport-boundary sketch (provisional, unconfirmed)

Implements the declaration in `deploy/wireguard/origin-transport-boundary.md`
using Windows Firewall (`netsh advfirewall` / `New-NetFirewallRule`). This is
a sketch to translate at inspection time, not a script to run blind.

```powershell
# The one permitted inbound socket (C1a). No source-address restriction:
# the laptop's address changes as it moves; WireGuard's own handshake
# authenticates the peer, not the source IP.
New-NetFirewallRule -DisplayName "WireGuard transport - C1a" `
    -Direction Inbound -Protocol UDP -LocalPort 51820 -Action Allow

# Confirm the default inbound policy for this profile is Block, so
# everything not explicitly allowed above stays closed.
Get-NetFirewallProfile | Select-Object Name, DefaultInboundAction
```

Do **not** add: an inbound allow rule for TCP 443/80/8000/8188
(contracts/origin-entry.md O2), an inbound allow rule for RDP/3389, SMB/445,
or any other management port reachable from the Internet (SC-018 #7), a rule
scoped to "Any" remote address without also being scoped to this exact
program/port pair, or a router-level port-forwarding entry pointing at this
host (that would be the router forwarding FR-041 forbids as a workaround).

`netsh` equivalent, for reference only:

```text
netsh advfirewall firewall add rule name="WireGuard transport - C1a" dir=in action=allow protocol=UDP localport=51820
```
