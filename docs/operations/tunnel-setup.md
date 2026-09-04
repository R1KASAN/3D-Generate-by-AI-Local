# WireGuard Tunnel Setup — Edge ↔ GPU Laptop

This is the operator runbook for the tunnel that lets the GPU laptop serve
`https://<public-hostname>/` from any network — university, home, mobile
hotspot — without ever touching DNS, the public IP, the Caddyfile, or the
tunnel addressing again after initial setup. See
`C:\Users\MetaHosP\.claude\plans\router-ai-eventual-tide.md` for the full
architecture and rationale; this file is the mechanical how-to.

## Prerequisites

- Edge server holds `161.200.90.4` (never `.3` — see the owner-gate).
- Border firewall permits inbound `443/tcp`, `80/tcp`, and **`51820/udp`**
  to `161.200.90.4`. If 51820/udp cannot be opened, see the fallback paths
  in the plan (WireGuard on 443/udp, SSH reverse tunnel, Tailscale) before
  proceeding with this runbook.
- WireGuard installed on both machines.

## 1. Generate key pairs

On each machine:

```powershell
wg genkey | Tee-Object laptop.key | wg pubkey | Tee-Object laptop.pub
```

(substitute `edge.key`/`edge.pub` on the edge). Keep the private key files
out of the repository — `deploy/wireguard/*.conf` (the filled-in configs,
not the `.example` templates) is already git-ignored for this reason.

## 2. Fill in the configs

Copy `deploy/wireguard/edge.conf.example` → `edge.conf` on the edge, and
`deploy/wireguard/upstream.conf.example` → `upstream.conf` on the laptop.
Fill in the real keys. Do not change `AllowedIPs` from the narrow `/32`
values in the templates — see the templates' own comments for why widening
this breaks the design (it would turn the app tunnel into a full VPN).

## 3. Bring the tunnel up

Edge first (it has no `Endpoint` to dial, so it just needs to be listening):

```powershell
wireguard /installtunnelservice C:\path\to\edge.conf
```

Then the laptop:

```powershell
wireguard /installtunnelservice C:\path\to\upstream.conf
```

Verify from the laptop:

```powershell
ping 10.10.0.1
```

If this fails, see **Troubleshooting** below before touching anything else.

## 4. Confirm the service name matches `web.xml`

`deploy/windows/services/web.xml` depends on a service named
`WireGuardTunnel$upstream`. WireGuard for Windows names the tunnel service
`WireGuardTunnel$<name-of-the-conf-file-without-extension>` — if you saved
the laptop's config as `upstream.conf`, the service is
`WireGuardTunnel$upstream` and no further change is needed. If you used a
different filename, either rename the file or update the `<depend>` entry
in `web.xml` to match — they must agree exactly or the Windows service
manager cannot resolve the dependency and `Local3D-Web` will fail to start.

## 5. Start the app services and watch the startup chain

```powershell
Restart-Service Local3D-ComfyUI, Local3D-API, Local3D-Web
```

`Local3D-Web` runs `scripts/windows/start_web_service.ps1`, which waits for
the tunnel address to exist and for the edge to answer a ping before
calling `next start`. Watch its log
(`deploy/windows/services/Local3D-Web.out.log`) for the "Tunnel is live"
line.

## 6. Install the recovery watchdog

Register `scripts/windows/watchdog_tunnel.ps1` as a Scheduled Task on the
laptop, running every 5 minutes as SYSTEM/an administrator account:

```powershell
$action = New-ScheduledTaskAction -Execute 'powershell.exe' `
  -Argument '-NoProfile -ExecutionPolicy Bypass -File "C:\path\to\scripts\windows\watchdog_tunnel.ps1"'
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 5) -RepetitionDuration ([TimeSpan]::MaxValue)
Register-ScheduledTask -TaskName 'Local3D Tunnel Watchdog' -Action $action -Trigger $trigger -RunLevel Highest
```

## Troubleshooting

**`ping 10.10.0.1` fails from the laptop, tunnel address is assigned**
Almost always one of: (a) the edge's border firewall does not actually
have 51820/udp open yet — confirm with IT, not just the request; (b) the
laptop's current network blocks outbound UDP (hotel/enterprise Wi-Fi) — see
the plan's fallback paths; (c) `PersistentKeepalive` is missing from
`upstream.conf` and the NAT session expired — re-check the config against
the template; (d) the McAfee VPN adapter is still active and has taken the
default route — disable/remove it (Stage 4 of the plan).

**Tunnel was fine, then died after ~30–60 seconds of inactivity, no changes made**
Missing `PersistentKeepalive = 25` on the laptop side. This is the single
most common WireGuard-behind-NAT failure and looks identical to "it just
randomly stopped working."

**`Local3D-Web` won't start, log shows a timeout waiting for the tunnel**
Check `WireGuardTunnel$upstream` is actually running
(`Get-Service WireGuardTunnel$upstream`) before assuming the app is at
fault — the dependency chain exists specifically so this is diagnosed at
the tunnel layer, not the app layer. `scripts/windows/watchdog_tunnel.ps1`
makes the same layer distinction for ongoing operation.

**Need to switch to a fallback transport (border firewall won't open UDP)**
1. **WireGuard on 443/udp** — same setup, change `ListenPort`/`Endpoint`
   to 443 on both configs. Confirm with IT that UDP/443 (not just TCP/443)
   is actually permitted before assuming this works.
2. **SSH reverse tunnel** — `autossh -M 0 -R 3000:localhost:3000 <edge-user>@161.200.90.4`
   run as a Windows service via NSSM or similar, with the same "wait
   before bind" discipline as `start_web_service.ps1`.
3. **Tailscale** — replaces WireGuard entirely; simplest to operate but
   depends on Tailscale's own relay infrastructure when direct/NAT
   traversal fails.
