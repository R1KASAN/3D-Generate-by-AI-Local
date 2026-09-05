# Linux origin transport-boundary sketch (provisional, unconfirmed)

Implements the declaration in `deploy/wireguard/origin-transport-boundary.md`
using `nftables` (or `ufw`/`iptables` equivalents — pick one, do not stack
multiple firewall tools on the same origin). This is a sketch to translate
at inspection time, not a script to run blind.

```text
# Default-deny inbound, as everywhere else on this origin.
table inet filter {
  chain input {
    type filter hook input priority 0; policy drop;

    # The one permitted inbound socket (C1a). No source-address restriction:
    # the laptop's address changes as it moves; WireGuard's own handshake
    # authenticates the peer, not the source IP.
    udp dport 51820 accept comment "wireguard transport - C1a"

    # Everything else stays dropped by the default policy above. Do not add
    # a broad "established,related" catch-all rule wider than this host's
    # own outbound connections require.
  }
}
```

`ufw` equivalent, for reference only:

```text
ufw default deny incoming
ufw allow 51820/udp comment "wireguard transport - C1a"
```

Do **not** add: a rule for TCP 443/80/8000/8188 (contracts/origin-entry.md
O2), a rule for SSH/22 or any other management port reachable from the
Internet (SC-018 #7), a permissive `0.0.0.0/0 -> any` rule, or a NAT/DNAT
rule forwarding a router port to this host (that would be the router
forwarding FR-041 forbids as a workaround).
