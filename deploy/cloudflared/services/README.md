# cloudflared Service Units — Provisional

**Status**: Provisional until the approved origin's operating system is physically inspected.

`specs/003-outbound-tunnel-entry/research.md` (R1) and `evidence/public-deployment/operator-inputs.md` both record the origin OS as unverified. The machine inspected so far in this workspace is the GPU laptop (Windows), not the approved origin holding `161.200.90.4`. Assuming the origin is Windows because the laptop is would repeat a mistake this project has already corrected once — see `evidence/public-deployment/allocation-memo-review.md`.

## What is OS-independent (already usable)

- `../config.yml.example` — the `cloudflared` config format is identical on every platform
- The credential storage and rotation procedure in `../README.md`
- The contract in `specs/003-outbound-tunnel-entry/contracts/origin-entry.md`

## What must wait for inspection

Only the **service-manager unit** that keeps `cloudflared` running and auto-starts it on boot is OS-specific:

| Origin OS (if confirmed) | Mechanism | File to add here |
|---|---|---|
| Windows | WinSW-wrapped service, following the pattern in `deploy/windows/services/*.xml` | `cloudflared.xml` |
| Linux (systemd) | `cloudflared service install` generates a systemd unit | `cloudflared.service` (reference only — the real one is installed by the tool) |

Do not add a unit file here speculatively. When the origin OS is confirmed (task T065 in `specs/003-outbound-tunnel-entry/tasks.md`), add the matching file and remove this caveat.

## Startup requirement regardless of OS

Per `contracts/origin-entry.md` O7, the connector starts automatically after reboot, in dependency order, with readiness verified before the origin advertises local health. It must **not** wait on the GPU laptop being reachable — an origin that comes up while the laptop is down is the exact condition the project-controlled unavailable page (FR-025) exists to handle.
