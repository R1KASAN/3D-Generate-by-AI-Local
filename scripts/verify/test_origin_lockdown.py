"""Fail-closed external probe for the single-node application boundary.

This script is only corroborating evidence from an explicitly off-campus
network. It never treats a timeout as proof of lockdown and probes only the
four application ports; feature 004 has no other origin transport listener.
"""

from __future__ import annotations

import argparse
import socket
import sys

APPROVED_ORIGIN_ADDRESS = "161.200.90.4"
PROHIBITED_TCP_PORTS = (3000, 8000, 8080, 8188)
PASS = "PASS"
FAIL = "FAIL"
INCONCLUSIVE = "INCONCLUSIVE"
CONNECTED = "connected"
REFUSED = "refused"
RESET = "reset"
TIMEOUT = "timeout"
UNKNOWN = "unknown-error"


def classify_probe(outcome: str) -> tuple[str, str]:
    if outcome == CONNECTED:
        return FAIL, "a direct application listener accepted the TCP connection"
    if outcome == REFUSED:
        return PASS, "connection refused - no application listener"
    if outcome == RESET:
        return PASS, "connection reset - no application response"
    if outcome == TIMEOUT:
        return INCONCLUSIVE, "silently dropped; not proof of lockdown"
    return INCONCLUSIVE, f"unclassifiable outcome {outcome!r}; fail closed"


def overall_verdict(verdicts: list[str]) -> str:
    if FAIL in verdicts:
        return FAIL
    if INCONCLUSIVE in verdicts or not verdicts:
        return INCONCLUSIVE
    return PASS


def probe_tcp(address: str, port: int, timeout: float) -> str:
    try:
        with socket.create_connection((address, port), timeout=timeout):
            return CONNECTED
    except ConnectionRefusedError:
        return REFUSED
    except (ConnectionResetError, ConnectionAbortedError):
        return RESET
    except (TimeoutError, socket.timeout):
        return TIMEOUT
    except OSError:
        return UNKNOWN


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin-address", default=APPROVED_ORIGIN_ADDRESS)
    parser.add_argument("--ports", type=int, nargs="+", default=list(PROHIBITED_TCP_PORTS))
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument("--confirm-off-campus", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if not args.confirm_off_campus:
        print("REFUSED: add --confirm-off-campus before recording external evidence", file=sys.stderr)
        return 2
    if args.origin_address != APPROVED_ORIGIN_ADDRESS:
        print(f"REFUSED: only the approved origin address {APPROVED_ORIGIN_ADDRESS} may be probed", file=sys.stderr)
        return 2
    if args.timeout <= 0 or any(not 1 <= port <= 65535 for port in args.ports):
        print("REFUSED: invalid timeout or port", file=sys.stderr)
        return 2
    verdicts: list[str] = []
    for port in args.ports:
        verdict, why = classify_probe(probe_tcp(args.origin_address, port, args.timeout))
        verdicts.append(verdict)
        print(f"{verdict}: tcp/{port} - {why}")
    result = overall_verdict(verdicts)
    if result == PASS:
        print("PASS: all application ports were unambiguously refused or reset")
        return 0
    print(f"{result}: direct application boundary is not proven", file=sys.stderr)
    return 1 if result == FAIL else 3


if __name__ == "__main__":
    raise SystemExit(main())
