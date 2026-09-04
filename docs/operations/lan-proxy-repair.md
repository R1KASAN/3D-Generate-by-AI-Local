# Runbook: Repair LAN Web Proxy

**Owner:** Windows Server Operator | **Frequency:** As needed
**Last Updated:** 2026-09-04 | **Last Run:** Not yet verified after repair

## Purpose

Restore the private-LAN web entry when all Local3D services are running but
`http://<server-lan-ip>:3000/` is unreachable. This procedure repairs only the
LAN port proxy from the server's private address to the loopback-only web
service. It does not create router forwarding or Internet exposure.

## Prerequisites

- [ ] Run on the Windows Local3D server in an elevated PowerShell session.
- [ ] Confirm the server's current private LAN IPv4 address with `ipconfig`.
- [ ] Confirm `Local3D-ComfyUI`, `Local3D-API`, and `Local3D-Web` are running.
- [ ] Use only a private RFC1918 address; do not substitute a Public IP.

## Procedure

### Step 1: Confirm the services and current LAN address

```powershell
Get-Service Local3D-ComfyUI, Local3D-API, Local3D-Web
ipconfig
```

**Expected result:** All three services report `Running`. Record the active
Wi-Fi or Ethernet IPv4 address, for example `172.20.10.6`.

**If it fails:** Start only the stopped service in dependency order: ComfyUI,
API, then Web. Do not continue until all three report `Running`.

### Step 2: Confirm the loopback web service works

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:3000/
```

**Expected result:** The command returns `StatusCode` 200.

**If it fails:** This is a web-service problem, not a LAN proxy problem. Check
the `Local3D-Web` service and its logs before changing the proxy.

### Step 3: Recreate the LAN port proxy

Replace `172.20.10.6` only if `ipconfig` shows a different current private LAN
address.

```powershell
netsh interface portproxy delete v4tov4 listenaddress=172.20.10.6 listenport=3000 protocol=tcp

netsh interface portproxy add v4tov4 listenaddress=172.20.10.6 listenport=3000 connectaddress=127.0.0.1 connectport=3000 protocol=tcp
```

**Expected result:** The private LAN entry maps
`172.20.10.6:3000` to `127.0.0.1:3000`.

**If it fails:** Confirm PowerShell is elevated and that the supplied address is
currently assigned to the server. Do not use a router or Public IP as the
listen address.

### Step 4: Verify the LAN entry on the server

```powershell
Invoke-WebRequest -UseBasicParsing http://172.20.10.6:3000/
```

**Expected result:** The command returns `StatusCode` 200.

**If it fails:** Check the current proxy mapping with:

```powershell
netsh interface portproxy show v4tov4
```

Then confirm the `Local3D LAN Web Entry` Windows Firewall rule remains enabled.

### Step 5: Verify from a second LAN device

From a phone or another computer connected to the same private Wi-Fi/LAN, open:

```text
http://172.20.10.6:3000/
```

**Expected result:** The Local3D web page opens. Do not access ports `8000` or
`8188` from the second device; they must remain private.

## Verification

- [ ] `http://127.0.0.1:3000/` returns HTTP 200 on the server.
- [ ] `http://<server-lan-ip>:3000/` returns HTTP 200 on the server.
- [ ] A second LAN device opens the same LAN URL.
- [ ] Ports 8000 and 8188 remain unreachable from the second LAN device.

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| Loopback URL fails | Local3D-Web is not serving | Check the Local3D-Web service and logs. |
| LAN URL fails but loopback succeeds | Stale or absent port proxy | Repeat Step 3 with the current private LAN IP. |
| Second device fails but server LAN URL succeeds | Different Wi-Fi/VLAN or client isolation | Connect both devices to the same private LAN and disable client isolation if the network owner permits it. |
| Port 8000 or 8188 opens from LAN | Private-service boundary failure | Stop public/LAN use and repair the firewall/binding before continuing. |

## Rollback

To remove only the LAN proxy entry, run this as Administrator with the current
private LAN address:

```powershell
netsh interface portproxy delete v4tov4 listenaddress=172.20.10.6 listenport=3000 protocol=tcp
```

This does not affect loopback access at `127.0.0.1:3000`.

## Escalation

| Situation | Contact | Method |
|---|---|---|
| A non-private address is required | Project Owner | Stop and request a public-deployment decision. |
| Internal API or ComfyUI ports are reachable | Project Owner / Windows administrator | Treat as a security issue and repair the boundary before use. |
| The LAN proxy will not bind after Steps 1-4 | Windows administrator | Provide sanitized service and proxy output. |

## Superseded by the public/mobile deployment (2026-09-04)

The LAN portproxy approach this runbook repairs is being replaced by the
WireGuard-tunnel architecture in
`C:\Users\MetaHosP\.claude\plans\router-ai-eventual-tide.md` and
`docs/operations/public-cutover.md`. Once that cutover happens:

- `deploy/firewall/configure-upstream-boundary.ps1` **removes the
  `172.20.10.6:3000` portproxy entry permanently** as one of its
  preconditions (it refuses to run at all while any portproxy entry
  exists) and removes the `Local3D LAN Web Entry` firewall rule.
- **Do not recreate this portproxy afterward.** It was found still holding
  a live listening socket for an address (`172.20.10.6`) the laptop no
  longer had — if the laptop ever rejoins a `172.20.10.x`-style hotspot
  network again post-cutover, a stale portproxy entry would silently
  reopen port 3000 with no firewall scoping. `Local3D-Web` binds the
  WireGuard tunnel address (`10.10.0.2`) instead, which is not reachable
  from an ordinary LAN/hotspot at all.
- This runbook remains valid only for a machine that is still running the
  older LAN-only topology and has not yet been through public cutover.

## History

| Date | Run By | Notes |
|---|---|---|
| 2026-09-04 | Codex diagnostic | Found a configured but non-listening LAN proxy for `172.20.10.6:3000`; repair commands recorded for operator execution. |
| 2026-09-04 | Claude (public-deployment planning) | Superseded by the WireGuard-tunnel architecture; this portproxy is removed permanently at cutover, not repaired. |
