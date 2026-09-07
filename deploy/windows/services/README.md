# Single-node Windows service package

These WinSW definitions supervise one local machine only. Every application
listener is loopback-bound: ComfyUI `127.0.0.1:8188`, FastAPI
`127.0.0.1:8000`, Next.js `127.0.0.1:3000`, and Caddy
`127.0.0.1:8080`. The dependency order is ComfyUI → API → Web → Caddy.

There is no WireGuard origin, second server, named Cloudflare tunnel, or
automatic cloudflared service in this package. Start the development tunnel
manually with `deploy/cloudflared/quick-tunnel.md`.

Install the reviewed WinSW binary with the hash-verified helper:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/windows/install_winsw_services.ps1 `
  -ProjectRoot (Get-Location).Path -WinSWPath C:\path\to\WinSW-x64.exe `
  -ExpectedWinSWSha256 <64-hex-sha256> -StartServices
```

The helper requires elevation, grants the restricted LocalService account only
the required read/execute and runtime-storage permissions, and installs no
credentials. Run `scripts/windows/verify_services.ps1` after installation.
