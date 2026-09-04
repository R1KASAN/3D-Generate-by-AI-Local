# Phase 10 Windows service package

These WinSW v2 definitions keep the application services unattended while
preserving the private-service boundary:

| Service | Process | Bind | Depends on |
|---|---|---|---|
| `Local3D-ComfyUI` | ComfyUI Python runtime | `127.0.0.1:8188` | — |
| `Local3D-API` | FastAPI/Uvicorn | `127.0.0.1:8000` | `Local3D-ComfyUI` |
| `Local3D-Web` | Next.js production server | `10.10.0.2:3000` (WireGuard tunnel address) | `WireGuardTunnel$upstream`, `Local3D-API` |

`Local3D-Web` binds the WireGuard tunnel address, not loopback, so the
public edge server (`161.200.90.4`) can reach it over the tunnel while
`Local3D-API` and `Local3D-ComfyUI` stay loopback-only. It starts via
`scripts/windows/start_web_service.ps1`, which waits for the tunnel address
to exist and for the edge to be reachable before invoking `next start` -
see `docs/operations/tunnel-setup.md`. This depends on the WireGuard
tunnel service the operator names when installing WireGuard for Windows;
`WireGuardTunnel$upstream` in `web.xml` must match that name exactly or the
`<depend>` will fail to resolve.

Install WinSW beside each copied XML and wrapper executable under a
machine-local installation root. The definitions use `%BASE%` so the project
can be copied without rewriting the API/web paths. Replace the machine-specific
ComfyUI path in `comfyui.xml` only when the audited runtime is installed at a
different location; changing it creates a new operator verification run.

The services are configured for the built-in `LocalService` identity. The
operator must grant that identity read/execute access to the application and
ComfyUI runtime directories plus write access only to the application storage
and required ComfyUI runtime directories. Do not put a password or token in
these files.

The repository does not download or commit a service wrapper. An administrator
must obtain the reviewed WinSW v2 binary through the approved operator channel,
record its SHA-256, then install it with the guarded helper:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/windows/install_winsw_services.ps1 `
  -ProjectRoot (Get-Location).Path `
  -WinSWPath C:\path\to\WinSW-x64.exe `
  -ExpectedWinSWSha256 <64-hex-sha256> `
  -StartServices
```

The helper refuses non-elevated sessions and hash mismatches. It creates only
the ignored wrapper binaries/config copies in this service directory and never
stores credentials.

Run the verifier from the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/windows/verify_services.ps1 `
  -ProjectRoot (Get-Location).Path -RunGeneration
```

The verifier records static definition checks even when the services are not
installed. It returns a blocked evidence result until all three services are
installed, running under the restricted identity, healthy in dependency order,
and a real post-service generation succeeds.

`verify_reboot_recovery.ps1 -ExecuteReboot` is intentionally explicit and must
only be run by an administrator who has approved a disruptive machine reboot.
