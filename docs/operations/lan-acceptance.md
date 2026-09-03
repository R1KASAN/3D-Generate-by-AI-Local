# LAN Acceptance Checklist (T082)

Run this checklist from a second physical device on the same private LAN. The
Windows server address and the approved entry URL must be supplied by the
operator; do not use `127.0.0.1`, the server itself, or a public forward.

On the Windows server, the owner-approved Phase 10 entry is a Windows TCP
forward bound only to the server's current RFC1918 address and port `3000`. It
targets the loopback Next.js service at `127.0.0.1:3000`; Next.js proxies
same-origin `/api` requests to the loopback API. Configure it from an elevated
PowerShell at the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/windows/configure_lan_boundary.ps1 `
  -LanAddress <server-private-lan-ip> -OwnerApproved
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/windows/verify_lan_boundary.ps1 `
  -LanAddress <server-private-lan-ip>
```

The firewall rule permits only `LocalSubnet` clients. This is LAN acceptance
infrastructure, not Internet publication or authorization for router forwarding.

## Preconditions

- [ ] Phase 9 gate is `PASS`.
- [ ] The three Phase 10 services are installed and running in dependency order.
- [ ] The approved LAN entry path is reachable from this client.
- [ ] Ports 8000 and 8188 remain loopback-only and are not used by the browser.
- [ ] A fresh valid JPEG or PNG fixture is available on this client.

## Flow

- [ ] Open the approved LAN entry path from this device.
- [ ] Upload one valid JPEG/PNG and record the opaque Job ID only.
- [ ] Observe `queued` and/or `processing` through the web UI.
- [ ] Refresh the page during processing; the same job state and result remain
      available without resubmission.
- [ ] Wait for `completed` and open the textured GLB preview.
- [ ] Exercise rotate, zoom, pan, and reset-view controls.
- [ ] Download the GLB through the web UI.
- [ ] Compare downloaded byte count and SHA-256 with the server-published
      result; they must be identical.
- [ ] Record timestamps, Job ID, artifact hash, browser/device label, and
      redacted screenshots in `evidence/lan/full-flow.md`.

## Stop conditions

Stop and record `FAIL` if the browser reaches ComfyUI directly, if a second
submission occurs after refresh, if preview controls do not work, or if the
download bytes differ from the validated server result. Record `BLOCKED` when
no second client or approved LAN entry path is available.
