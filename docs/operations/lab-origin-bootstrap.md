# Runbook: Lab Origin Bootstrap (Stage 0 — first access)

**Owner:** Whoever has physical or console access to the lab origin | **Frequency:** Once, before `tunnel-setup.md`
**Status:** No connection exists yet. Institutional/administrative authorization to access the machine (professor approval) is **not the same thing** as a technical connection method — this runbook exists to establish the second one safely, without weakening the boundary the previous phase just built (SC-018).

This is Stage 0. Do not skip to `tunnel-setup.md` before it: that runbook assumes "authorized physical or remote access" already exists and does not say how to get it safely. This one does, and only this one.

## Why this needs its own runbook

SC-018 requires the approved origin to have **no** SSH/RDP/VNC or other management listener reachable directly from the Internet — that rule exists because, after Option A, the WireGuard transport port is supposed to be the origin's *only* Internet-reachable socket. Standing up SSH the naive way (open to `0.0.0.0/0`) to make future access easier would quietly violate the exact boundary Phase 6 just built and verified. This runbook exists so that doesn't happen by accident under time pressure.

## Step 0 — First contact: console only, nothing installed yet

Whoever has physical access should, before installing or opening anything:

1. Confirm the machine's OS and version. Record it, masked, in `evidence/public-deployment/operator-inputs.md`, replacing the `PENDING TARGET INSPECTION` row (tasks.md T065).
2. Confirm this machine actually holds the approved address (`ip addr` / `ipconfig`), and record the outbound egress address the same way (T065).
3. Confirm whether `161.200.90.4` is directly bindable on this host, and whether the host directly receives UDP without router forwarding — the two items research.md R5/R9 and tasks.md T066/T066b need. **If the UDP-reachability check fails, stop here: Option A is not feasible for this target (FR-041), and everything below this line does not apply until a transport redesign is decided.**
4. List what is currently listening (`ss -tulpn` / `netstat -ano` + `Get-NetTCPConnection`), for awareness only. Do not close, open, or change anything yet — this is inventory, not configuration.

None of this needs a remote connection. If T066b fails at this step, do not proceed to Step 1.

## Step 1 — Decide the ongoing management channel (an owner decision, not a default)

Once UDP reachability is confirmed, someone with authority over the machine (the professor, lab admin, or the project owner) needs to pick **one** of the following and record which. This is a genuine decision with a security trade-off, not something to default silently:

| Option | What it is | SC-018 impact | Recommended when |
|---|---|---|---|
| **A — Console only** | No persistent remote shell at all; every change is made at the physical keyboard | Zero — no new listener of any kind | Changes are rare and someone can reasonably get to the machine |
| **B — VPN/bastion-scoped SSH** | `sshd` bound normally, but the origin firewall accepts SSH only from the university's existing VPN or bastion egress range — never `0.0.0.0/0` | Technically a listening socket, but not reachable from the open Internet, so it does not create the exposure SC-018 exists to prevent | Remote changes are needed and an institutional VPN/bastion already exists |
| **C — Internet-facing SSH** | `sshd` reachable from any source address | **Weakens the exact boundary Phase 6 verified.** Needs written owner risk-acceptance, naming the exposure explicitly, before it is used | Only if neither A nor B is available — do not choose this by default |

Record the choice, the date, and who decided it in `evidence/public-deployment/management-access.md` before proceeding. If C is chosen, that record must also carry the owner's written risk acceptance — mirroring how `fallback-policy.md` records the zrok TLS exposure acceptance, not a rubber stamp.

## Step 2 — If Option B (or C) is chosen: set it up key-only

1. Generate a **fresh** ED25519 keypair on the client that will connect (the GPU laptop, or an admin workstation) — do not reuse a key from anywhere else:
   ```bash
   ssh-keygen -t ed25519 -C "lab-origin-bootstrap-2026-09"
   ```
2. Install only the **public** key in the server's `authorized_keys` for a non-root, least-privilege account. Never transmit or store the private key anywhere but the client that generated it.
3. In `sshd_config`: `PasswordAuthentication no`, `PermitRootLogin no`, `PubkeyAuthentication yes`. Restart `sshd` and confirm password login is now rejected before disconnecting the console session that made the change — do not lock yourself out.
4. Scope the firewall rule to the exact source range chosen in Step 1 (the VPN/bastion CIDR for Option B — never `Any`). This is a firewall change on a shared system: if anyone other than the person following this runbook administers the origin, confirm with them first.
5. Test the connection from the client, confirm key-only login works, and record the account name and the key's public fingerprint (never the private key) in `evidence/public-deployment/management-access.md`.

## Step 3 — Continue into the existing procedure

Once a channel exists and Step 0's T065/T066/T066b findings are recorded, proceed to `docs/operations/tunnel-setup.md` Procedure steps 1–5 (Caddy, cloudflared, the interim Quick Tunnel test, and origin service installation) exactly as written there. Do not repeat Step 0 or Step 1 — they are one-time.

## What not to do at any point in this runbook

- Do not open SSH, RDP, or VNC to `0.0.0.0/0` as a shortcut "to get started" and narrow it later — narrow it first.
- Do not add any TCP application port as an inbound firewall rule on the origin (contracts/origin-entry.md O2).
- Do not enable router port forwarding for SSH, WireGuard, or anything else (FR-003, FR-041).
- Do not treat physical/administrative authorization alone as sufficient to skip Step 0's UDP-reachability check — authorization to be on the machine is not evidence about what the network path in front of it actually permits.
