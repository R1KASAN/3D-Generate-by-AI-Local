# Phase 10 Operator Handoff

This handoff identifies the real-world actions required before T080-T084 may be
marked `[X]`. LAN configuration requires the explicit `-OwnerApproved` switch
and creates only a local-subnet web entry; it never exposes API or ComfyUI.

## 1. Install and verify services as administrator

Open an elevated PowerShell session on the Windows NVIDIA server. Obtain the
reviewed WinSW v2 binary through the operator-approved channel and record its
SHA-256 locally. Do not paste the binary hash together with credentials or
capability tokens into chat.

From the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/windows/install_winsw_services.ps1 `
  -ProjectRoot (Get-Location).Path `
  -WinSWPath C:\path\to\WinSW-x64.exe `
  -ExpectedWinSWSha256 <64-hex-sha256> `
  -StartServices

powershell -NoProfile -ExecutionPolicy Bypass -File scripts/windows/verify_services.ps1 `
  -ProjectRoot (Get-Location).Path -RunGeneration
```

The service verifier must report all three services running under `LocalService`,
the dependency order `Local3D-ComfyUI -> Local3D-API -> Local3D-Web`, healthy
loopback endpoints, and one new real textured GLB. If the verifier is not
`PASS`, stop and retain its sanitized evidence.

## 2. Reboot recovery

Only after the service verifier passes, confirm the reboot is approved and run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/windows/verify_reboot_recovery.ps1 `
  -ProjectRoot (Get-Location).Path -ExecuteReboot
```

The script registers an on-start verification task before issuing the reboot.
Do not open a terminal to start any application after reboot. The resulting
evidence must show automatic startup, state reconciliation, and a new textured
generation.

## 3. Second-device LAN proof

On the Windows server, configure and verify the approved private entry from an
elevated PowerShell. Replace the example with the server's current RFC1918 LAN
address:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/windows/configure_lan_boundary.ps1 `
  -LanAddress <server-private-lan-ip> -OwnerApproved
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/windows/verify_lan_boundary.ps1 `
  -LanAddress <server-private-lan-ip>
```

From a separate physical device on the same private LAN, use the approved LAN
entry URL. Complete [lan-acceptance.md](lan-acceptance.md), recording only
sanitized Job IDs, byte counts, hashes, timestamps, and redacted screenshots.

For the boundary test, set the two job tokens only in the second device's
process environment and run:

```powershell
$env:LAN_JOB_A = '<first-job-id>'
$env:LAN_TOKEN_A = '<first-job-token>'
$env:LAN_JOB_B = '<second-job-id>'
$env:LAN_TOKEN_B = '<second-job-token>'
python scripts/verify/test_lan_boundary.py `
  --server-host <server-private-lan-ip> `
  --entry-url <approved-lan-entry-url> `
  --client-label <second-device-label>
```

The output must show the approved entry path working, ports 8000 and 8188
unreachable, and uniform wrong-job 404 responses. Clear the environment
variables immediately after the run. Never place tokens in URLs, logs, evidence,
or chat.

## 4. Gate closeout

Update [phase-10-gate.md](../../evidence/lan/phase-10-gate.md) with the actual
commands, timestamps, Job IDs, hashes, service logs, and redacted screenshots.
Only when T080-T083 are all PASS may T084 and the five task markers in
`specs/001-local-3d-generation/tasks.md` be changed to `[X]`.
