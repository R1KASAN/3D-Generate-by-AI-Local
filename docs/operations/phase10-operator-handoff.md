# Feature 004 operator handoff

Feature 004 is the current authority. The complete deployment is one
Notebook/PC assigned `161.200.90.4`:

```text
Public user -> temporary HTTPS -> Cloudflare Quick Tunnel
-> cloudflared -> Caddy 127.0.0.1:8080
-> Web 127.0.0.1:3000 / FastAPI 127.0.0.1:8000
-> ComfyUI 127.0.0.1:8188 -> RTX 5070
```

There is no edge server, WireGuard, direct inbound application access, domain
purchase, DNS change, custom hostname, cloud GPU, or second application
server. A stable hostname is an approval-gated future step only.

## Operator gates

The following require an elevated/operator action and must not be claimed from
repository tests alone:

1. Install and start `Local3D-ComfyUI`, `Local3D-API`, `Local3D-Web`, and
   `Local3D-Caddy` from the reviewed WinSW definitions.
2. Remove or formally accept the existing operator-owned portproxy mappings;
   do not alter them from an unapproved shell.
3. Run `health_chain.ps1 -Json` with Caddy installed and confirm all local
   dependencies; Quick Tunnel and public-route checks remain separate.
4. Run controlled service restart and real reboot trials, recording durable job
   outcomes without tokens or user content.
5. From a genuinely off-campus network, run the external acceptance verifier
   with the actual temporary hostname and explicit attestation.

## Exact elevated installation command

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/windows/install_winsw_services.ps1 `
  -ProjectRoot (Get-Location).Path `
  -WinSWPath C:\path\to\WinSW-x64.exe `
  -ExpectedWinSWSha256 <64-hex-sha256> `
  -StartServices
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/windows/verify_services.ps1 `
  -ProjectRoot (Get-Location).Path
```

Never paste the hash alongside credentials, tokens, private URLs, or generated
assets. If installation is not elevated, leave the service gate MANUAL.

## Historical versus current evidence

Evidence under `evidence/feature-004/` is current only when it names the
single-node route and records an actual command/result. Earlier split-host,
WireGuard, inbound-edge, named-Tunnel, and feature-003 evidence remains
historical context and cannot close a feature-004 task. The current English
and Thai procedures are [windows-ai-server-runbook.en.md](windows-ai-server-runbook.en.md)
and [windows-ai-server-runbook.th.md](windows-ai-server-runbook.th.md); the
temporary entry procedure is [single-host-tunnel-setup.md](single-host-tunnel-setup.md).

## Reboot checklist

After an authorized reboot, verify services, loopback listeners on 3000/8000/
8080/8188, GPU and ComfyUI readiness, SQLite job reconciliation, output
revalidation, listener boundary, and only then a new Quick Tunnel. A reboot
task stays incomplete until the machine has actually rebooted and evidence is
captured.
