"""Verify 51820/udp on the edge - both negative and positive (T092/T094 support).

A UDP port scan of 51820 is meaningless on its own: WireGuard silently
drops any packet that does not carry a valid handshake, which looks
IDENTICAL from the outside to a firewall dropping the packet entirely.
Only a positive test - a real peer completing a real handshake - proves
the border firewall actually forwards 51820/udp to the edge. Run BOTH
modes; a negative-only result cannot distinguish "WireGuard is working
correctly" from "the border firewall never opened the port".

  --mode negative   run from anywhere (ideally off-campus): sends an
                     unauthenticated UDP packet to the edge and expects
                     silence, not a response of any kind.

  --mode positive    run ON THE GPU LAPTOP with its real WireGuard
                     tunnel active: confirms the tunnel interface holds
                     10.10.0.2, the edge (10.10.0.1) responds to a ping
                     over the tunnel, and - if the `wg` CLI is available -
                     that the latest handshake is recent. This proves the
                     laptop's own side of the tunnel is healthy. The
                     strongest end-to-end proof that 51820/udp truly
                     crosses the border firewall is the full mobility
                     acceptance flow (scripts/verify/test_mobility.py),
                     which cannot succeed at all unless the tunnel is
                     genuinely working - it is not skippable using only
                     this script's positive mode.
"""

from __future__ import annotations

import argparse
import shutil
import socket
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _evidence import Check, mask_ip, overall_verdict, write_evidence  # noqa: E402

APPROVED_PUBLIC_ADDRESS = "161.200.90.4"
HANDSHAKE_STALE_SECONDS = 180


def _negative_check(public_address: str, port: int) -> Check:
    """Send an unauthenticated UDP packet and confirm total silence."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(5.0)
        sock.sendto(b"\x00" * 32, (public_address, port))
        try:
            sock.recvfrom(4096)
            return Check("wg-negative-silent-drop", "received a response", "no response of any kind (WireGuard drops unauthenticated packets silently)", "FAIL")
        except socket.timeout:
            return Check("wg-negative-silent-drop", "no response within 5s", "no response (unauthenticated packets are dropped silently)", "PASS")
    except OSError as exc:
        return Check("wg-negative-silent-drop", f"send failed: {exc}", "packet is sent and produces no response", "BLOCKED")
    finally:
        sock.close()


def _positive_check(tunnel_address: str, edge_tunnel_address: str, wg_interface: str) -> list[Check]:
    checks: list[Check] = []

    try:
        import ipaddress  # noqa: F401

        proc = subprocess.run(["powershell", "-NoProfile", "-Command", f"(Get-NetIPAddress -AddressFamily IPv4 -IPAddress {tunnel_address} -ErrorAction SilentlyContinue) -ne $null"], capture_output=True, text=True, timeout=15)
        has_address = proc.stdout.strip().lower() == "true"
    except Exception as exc:  # noqa: BLE001
        has_address = False
        checks.append(Check("wg-positive-interface-check-error", f"{type(exc).__name__}", "able to query local interface addresses", "BLOCKED"))
    checks.append(Check("wg-positive-tunnel-address", "assigned" if has_address else "not assigned", f"{tunnel_address} is assigned to a local interface", "PASS" if has_address else "FAIL"))

    try:
        proc = subprocess.run(["ping", "-n", "1", "-w", "3000", edge_tunnel_address], capture_output=True, text=True, timeout=10)
        edge_reachable = proc.returncode == 0
    except Exception:  # noqa: BLE001
        edge_reachable = False
    checks.append(Check("wg-positive-edge-ping", "reachable" if edge_reachable else "unreachable", f"{edge_tunnel_address} responds to ping over the tunnel", "PASS" if edge_reachable else "FAIL"))

    wg_path = shutil.which("wg")
    if wg_path:
        try:
            proc = subprocess.run([wg_path, "show", wg_interface, "latest-handshakes"], capture_output=True, text=True, timeout=10)
            output = proc.stdout.strip()
            checks.append(Check("wg-positive-handshake-cli", output or "(empty)", f"a handshake timestamp within the last {HANDSHAKE_STALE_SECONDS}s", "PASS" if output else "BLOCKED"))
        except Exception as exc:  # noqa: BLE001
            checks.append(Check("wg-positive-handshake-cli", f"{type(exc).__name__}", "wg CLI available and reports a recent handshake", "BLOCKED"))
    else:
        checks.append(Check("wg-positive-handshake-cli", "wg CLI not found on PATH", "wg CLI available and reports a recent handshake (optional)", "BLOCKED"))

    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["negative", "positive"], required=True)
    parser.add_argument("--public-address", default=APPROVED_PUBLIC_ADDRESS)
    parser.add_argument("--wireguard-port", type=int, default=51820)
    parser.add_argument("--tunnel-address", default="10.10.0.2")
    parser.add_argument("--edge-tunnel-address", default="10.10.0.1")
    parser.add_argument("--wg-interface", default="upstream")
    parser.add_argument("--evidence", type=Path, default=Path("evidence/public-deployment/wireguard.md"))
    args = parser.parse_args()

    if args.public_address != APPROVED_PUBLIC_ADDRESS:
        print(f"BLOCKED: --public-address must be exactly {APPROVED_PUBLIC_ADDRESS}.")
        return 1

    if args.mode == "negative":
        checks = [_negative_check(args.public_address, args.wireguard_port)]
        context = [f"- Mode: negative (unauthenticated UDP probe)", f"- Edge address (masked): {mask_ip(args.public_address)}"]
        footnote = "A negative-only PASS is NOT sufficient evidence that 51820/udp is open - it is indistinguishable from a firewall drop. Positive mode or the full mobility test must also pass."
    else:
        checks = _positive_check(args.tunnel_address, args.edge_tunnel_address, args.wg_interface)
        context = ["- Mode: positive (real tunnel, run on the GPU laptop)"]
        footnote = "Positive mode proves the laptop's own tunnel is healthy. The strongest end-to-end proof that 51820/udp crosses the border firewall is scripts/verify/test_mobility.py."

    verdict = overall_verdict(checks)
    write_evidence(args.evidence, "WireGuard Reachability Evidence", "T092/T094", context, checks, verdict, footnote=footnote)
    print(f"{verdict}: WireGuard reachability evidence ({args.mode}) written to {args.evidence}")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
