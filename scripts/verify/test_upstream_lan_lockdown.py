"""Verify that the laptop web entry is not reachable from its physical LAN.

Run this from a second device on the laptop's physical LAN or Wi-Fi with
``--confirm-same-lan``. The target must be a private LAN address, never the
public origin. A connection that succeeds is a security failure; a refused or
filtered connection is the expected result after the tunnel-only boundary is
applied.
"""

from __future__ import annotations

import argparse
import ipaddress
import socket
import sys


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-address", required=True)
    parser.add_argument("--port", type=int, default=3000)
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--confirm-same-lan", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if not args.confirm_same_lan:
        print("REFUSED: add --confirm-same-lan only when running from another device on the physical LAN", file=sys.stderr)
        return 2
    try:
        target = ipaddress.ip_address(args.target_address)
    except ValueError:
        print("REFUSED: target must be a literal IP address", file=sys.stderr)
        return 2
    if not target.is_private or target.is_loopback:
        print("REFUSED: target must be a non-loopback private LAN address", file=sys.stderr)
        return 2
    if not 1 <= args.port <= 65535:
        print("REFUSED: port must be in the range 1..65535", file=sys.stderr)
        return 2

    try:
        with socket.create_connection((args.target_address, args.port), timeout=args.timeout):
            print("FAIL: physical-LAN client connected to the web-entry port", file=sys.stderr)
            return 1
    except (ConnectionRefusedError, ConnectionResetError, TimeoutError, OSError) as exc:
        print(f"PASS: physical-LAN connection was refused or filtered ({exc.__class__.__name__})")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
