# Public Cutover Runbook — Edge `161.200.90.4` + Mobile GPU Laptop

Operator procedure for Stage 3–6 of the public-deployment plan
(`C:\Users\MetaHosP\.claude\plans\router-ai-eventual-tide.md`). Read the
plan first — this file is the execution checklist, not the design
rationale.

## Non-negotiable constraint

`161.200.90.4` is the only approved public address. `161.200.90.3` is
allocated elsewhere and must never be configured, forwarded, or probed by
anything here — `deploy/firewall/configure-public-edge.ps1` refuses any
other address by design, and `tests/security/test_caddy_contract.py`
scans `deploy/` for the forbidden literal.

## Port policy (authoritative — do not let scripts/docs drift from this)

| Port | Proto | Purpose | Source |
|---|---|---|---|
| 443 | TCP | HTTPS (Caddy) | Any |
| 80 | TCP | ACME HTTP-01 + redirect only | Any |
| 51820 | UDP | WireGuard | Any (key-authenticated, not IP-filtered) |
| management | per Stage 0.1 decision | edge admin access | trusted source only |

## Prerequisites (Stage 0)

Confirm all of the following are answered **in writing** before starting:

- [ ] Edge management path decided and tested (SSH from a trusted source,
      or physical console) — **do this before any firewall change**
- [ ] Edge OS confirmed (Windows → `configure-public-edge.ps1`; Linux →
      an equivalent nftables/ufw ruleset, not yet written in this repo)
- [ ] Border firewall confirmed open: 443/tcp, 80/tcp, **51820/udp**
- [ ] DNS hostname assigned, or the owner has explicitly approved the
      IP-certificate fallback (see `.env.example`'s comment on
      `PUBLIC_HOSTNAME`)
- [ ] `161.200.90.3`'s actual use confirmed, so nothing collides with it

## Stage 3 — Edge

1. Confirm the management path works (SSH in, verify).
2. Confirm `161.200.90.4` is assigned and matches what an external "what is
   my IP" check reports (proves no NAT sits in front of the edge).
3. Follow `docs/operations/tunnel-setup.md` to bring up WireGuard on the
   edge.
4. Install Caddy. Copy `deploy/caddy/Caddyfile` and a filled-in
   `deploy/caddy/.env` (from `.env.example`) onto the edge.
   Run `caddy validate --config deploy/caddy/Caddyfile` and
   `python -m pytest tests/security/test_caddy_contract.py` — both must
   pass before Caddy is started for the first time.
5. Create the DNS A record → `161.200.90.4` (T089). Record it, with the IP
   masked, in `evidence/public-deployment/dns-router.md`.
6. Run `deploy/firewall/configure-public-edge.ps1` with the real
   `-PublicAddress 161.200.90.4`, `-CaddyPath`, `-ManagementSourceCidr`,
   and `-OwnerApproved`. **Open a new session and confirm management
   access still works before closing your current one.**
7. Start Caddy.

   > **This step is not quietly reversible.** ACME issuance publishes the
   > hostname to public Certificate Transparency logs permanently. Get
   > explicit owner sign-off before this step, not after.

8. Confirm the site currently serves the maintenance page (the laptop
   hasn't connected yet) — this proves `handle_errors` works.
9. Set Caddy and the WireGuard tunnel service to start automatically on
   boot.

## Stage 4 — Laptop

1. Remove the stale portproxy entry (`172.20.10.6:3000`) — see
   `docs/operations/lan-proxy-repair.md`.
2. Remove the `Local3D LAN Web Entry` firewall rule.
3. Disable/remove the McAfee VPN adapter.
4. Follow `docs/operations/tunnel-setup.md` to bring up the laptop side of
   the tunnel and confirm `ping 10.10.0.1` succeeds.
5. Confirm `deploy/windows/services/web.xml` and
   `scripts/windows/start_web_service.ps1` are in place, then restart the
   three `Local3D-*` services in dependency order.
6. Install the watchdog Scheduled Task (see `tunnel-setup.md` §6).
7. Run `deploy/firewall/configure-upstream-boundary.ps1 -EdgePeer 10.10.0.1 -OwnerApproved`,
   then `verify-upstream-boundary.ps1` and confirm it PASSes.
8. Confirm RDP stays disabled.
9. Set power settings: no sleep on AC, no sleep on lid close.
10. Do **not** remove Wi-Fi profiles or otherwise restrict the laptop to
    campus networks — mobility is the point.

## Verification (Stage 6 / T090–T094)

Run from a genuinely external vantage point (mobile data, home network, or
an off-campus VPS) — every script below refuses to record a PASS without
`--confirm-off-campus`:

```powershell
python scripts/verify/test_https_boundary.py --hostname <host> --public-ip 161.200.90.4 --confirm-off-campus
python scripts/verify/test_external_ports.py --public-address 161.200.90.4 --confirm-off-campus
python scripts/verify/test_wireguard_reachability.py --mode negative --confirm-off-campus
python scripts/verify/test_wireguard_reachability.py --mode positive   # run ON the laptop instead
python scripts/verify/test_public_auth.py --hostname <host> --confirm-off-campus
python scripts/verify/test_external_acceptance.py --hostname <host> --image <fixture.jpg> --confirm-off-campus
python scripts/verify/test_mobility.py --hostname <host> --confirm-off-campus
```

`test_mobility.py` is the project's actual acceptance test — see its
docstring. It must pass with **zero** changes to DNS, the public IP, the
Caddyfile, or WireGuard addressing during the run.

Evidence lands in `evidence/public-deployment/*.md`, all IP-masked per the
`evidence/lan/isolation-and-ports.md` convention.
