# Runbook: Outbound connector and private compute binding

**Owner:** Lab server operator | **Frequency:** Setup or recovery
**Updated:** 2026-09-06 | **Last live run:** BLOCKED — no authorized origin access

The origin runs the connector and the **origin pass-through** (Caddy). The laptop runs the **job service**, API, queue, storage, and AI engine. The public route is:

`visitor → Cloudflare → outbound cloudflared connection → loopback origin pass-through → private binding → laptop job service`

## Prerequisites

**First time only**: if no management channel to the origin exists yet, follow `docs/operations/lab-origin-bootstrap.md` before this runbook — it covers the OS/UDP-reachability checks and the safe way to establish that channel without opening a management listener SC-018 forbids. Skip straight to the steps below only once that is done.

Obtain authorized physical or remote access to the actual lab origin. The operator currently has only its approved address: no confirmed remote-management listener or connection method. Do not discover management ports by probing the public address. Inspect OS, interface assignment, egress, and local listeners after access is available; retain masked observations in `evidence/public-deployment/operator-inputs.md`.

The private binding remains the existing narrow WireGuard contract: laptop initiates, each peer permits only the other peer's `/32`, origin has no configured laptop Endpoint, and laptop retains keepalive. No public HTTP or management listener is allowed. The clarified contract selects Option A: one narrowly scoped WireGuard UDP transport listener is permitted on the approved origin. Restrict it to the approved origin address, the WireGuard UDP port, and the WireGuard service; peer public-key authentication is required. The laptop's changing source address means the firewall cannot use a fixed remote CIDR. Do not add router forwarding, application ports, management ports, or catch-all rules. No source-address binding until local ownership of the address is verified.

## Procedure

1. Verify the local baseline from the repository root:

   `uv run --project apps/api pytest tests/security apps/api/tests --import-mode=importlib -q`

   Expect all software checks to pass; GPU skips are not hardware evidence. Diagnose a failure before changing deployed services.

2. On the GPU laptop, keep API, ComfyUI, and Next.js on loopback. Use the existing trusted-LAN host port forward and the private-binding port forward. Never delete the trusted-LAN path at cutover. No feature 001 service depends on WireGuard. Once installed, `Start-Service Local3D-ComfyUI, Local3D-API, Local3D-Web` starts the application regardless of origin availability.

3. On the approved origin, install Caddy and cloudflared for its inspected OS. Render `deploy/caddy/.env.example` and `deploy/cloudflared/config.yml.example` outside Git. Replace template placeholders explicitly. Match the connector target to `http://127.0.0.1:8443`; the private upstream is configured only in Caddy. Render the maintenance directory for the OS. Run `caddy validate --config <rendered-Caddyfile>` before starting it. Do not install Origin CA or Authenticated Origin Pulls material.

4. For interim development, run on the **origin only**:

   `cloudflared tunnel --url http://127.0.0.1:8443`

   This is a temporary development hostname. Capture an off-LAN upload → generation → polling → browser preview → download. Do not call it the production identity or report concurrency/load as production characteristics. Named production routing follows `public-cutover.md` after its gates pass.

5. Install origin services using `deploy/cloudflared/services/` only after confirming the OS and actual service identities. Network readiness precedes connector and origin pass-through startup; local health is advertised only after readiness. Startup must succeed with the laptop down. Neither machine's boot depends on the other.

## Verification and recovery

On the laptop use `powershell -NoProfile -File scripts/windows/health_chain.ps1 -All`. Probe private binding, job service, GPU, and AI engine independently. GPU uses OS-level `nvidia-smi`. On the origin check connector readiness at `http://127.0.0.1:20241/ready`; this does not independently prove provider-edge availability. Test the provider edge from an external vantage point and record it separately.

Run the matrices in `specs/003-outbound-tunnel-entry/quickstart.md`: three reboots per machine, both boot orders, three Internet interruption/restores, each isolated layer failure, and binding return without restarting the app. Origin/connector down produces the provider error; it is not an application failure. Binding/job-service/engine failure requires the project unavailable response within five seconds, with no internal details.

Restart only the failed owned layer. After a dependency returns, allow the configured grace period and recheck its dependent. Stop after three failed recovery attempts at a layer. Never restart healthy laptop services to repair a connector fault.

## Rollback

From an authorized origin console stop the active connector process/service using its inspected service manager, and prevent its automatic restart. This works even when its config is invalid. Do not delete jobs, uploads, artifacts, or the LAN port forward. Record route disable and verify the LAN journey and unchanged existing results. Do not enable the legacy inbound proxy as rollback.

## Troubleshooting and escalation

| Symptom | Next action |
|---|---|
| No authorized origin access | Lab operator arranges physical access; leave all live-origin tasks blocked |
| Binding down, LAN healthy | Inspect local handshake/keepalive and approved transport; leave app running |
| Provider error | Inspect origin power, connector, and its outbound network from authorized access |
| Project unavailable response | Probe binding, job service, GPU, engine separately |
| Hostname never authorized | Keep public release blocked; development/demo only |
| Live hostname withdrawn | Use fallback only with recorded cause, start, owner recovery window, and separate zrok exposure acceptance |

Escalate access and transport permissions to the responsible lab/network operator through their existing authorized channel. The human operator obtains hostname consent; this runbook does not authorize contacting the domain owner on their behalf.
