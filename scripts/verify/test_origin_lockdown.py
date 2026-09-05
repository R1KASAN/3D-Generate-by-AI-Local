"""Verify the approved origin exposes no direct Internet-facing application
or management listener (feature 003, T054, FR-003, FR-004).

Feature 002 hardened a public :443 listener behind mTLS and treated a
rejected TLS handshake as proof of lockdown. Feature 003 removes that
listener entirely: the origin is reached only through an outbound connector
(contracts/origin-entry.md O1).

**Option A (2026-09-06) changes what "no inbound" means here.** The origin is
the WireGuard *responder* for the private compute link, so exactly one
narrowly scoped WireGuard **UDP** transport listener is permitted
(contracts/compute-link.md C1a). It is not an application or management
entry point. This script therefore:

  * probes **TCP only**, for application and management ports that must
    never accept a connection;
  * treats the permitted WireGuard UDP transport port as PERMITTED and
    refuses to probe it as if it were prohibited — conflating the UDP
    transport with its TCP twin is exactly the ambiguity that made the
    pre-Option-A version of this script unable to tell a violation from
    the approved design;
  * **fails closed.** Only an unambiguous refusal or reset counts as proof
    that nothing is listening. A silent drop (timeout) is consistent with
    lockdown but is indistinguishable from a broken path, a filtered
    upstream, or an unplugged laptop, so it is recorded INCONCLUSIVE and
    the run does not exit 0.

Remote probing can never be sufficient evidence on its own: a drop-all
firewall makes every closed port look identical to a filtered one, and an
unauthenticated UDP probe of a WireGuard listener gets no reply at all. The
authoritative evidence for the transport listener's scope is the
origin-local inventory in tasks.md T066a (SC-018); this script corroborates
it from outside and says so in its own output.
"""

from __future__ import annotations

import argparse
import socket
import sys


APPROVED_ORIGIN_ADDRESS = "161.200.90.4"

# The single inbound socket Option A permits, per contracts/compute-link.md
# C1a. Recorded as data so the contract test can assert it is never treated
# as a prohibited port.
PERMITTED_TRANSPORT_PROTOCOL = "udp"
PERMITTED_TRANSPORT_PORT = 51820

# TCP ports that must never accept a connection from the Internet: the
# former public entry (443/80), the application and engine ports, the proxy
# and metrics admin ports, and the management ports Out of Scope forbids
# outright (SSH, RDP, SMB, database, cache).
PROHIBITED_TCP_PORTS = (
    443, 80, 3000, 8000, 8080, 8443, 8188, 20241, 2019,
    22, 3389, 445, 5432, 6379, 9090,
)

PASS = "PASS"
FAIL = "FAIL"
INCONCLUSIVE = "INCONCLUSIVE"

# Probe outcomes, kept as plain strings so classification is testable
# without opening a socket.
CONNECTED = "connected"
REFUSED = "refused"
RESET = "reset"
TIMEOUT = "timeout"
UNKNOWN = "unknown-error"


def classify_probe(outcome: str) -> tuple[str, str]:
    """Map a probe outcome to (verdict, why).

    Fail-closed: anything that is not an unambiguous "nothing is listening"
    is refused as evidence. Only a completed connection is an outright FAIL,
    because only that proves a listener exists.
    """
    if outcome == CONNECTED:
        return FAIL, "a listener accepted the TCP connection"
    if outcome == REFUSED:
        return PASS, "connection refused - nothing is listening"
    if outcome == RESET:
        return PASS, "connection reset - nothing is serving"
    if outcome == TIMEOUT:
        return (
            INCONCLUSIVE,
            "silently dropped; consistent with lockdown but indistinguishable "
            "from a filtered path - not proof on its own",
        )
    return (
        INCONCLUSIVE,
        f"unclassifiable outcome {outcome!r}; recorded as inconclusive rather "
        "than assumed safe",
    )


def overall_verdict(verdicts: list[str]) -> str:
    """FAIL dominates; a single INCONCLUSIVE prevents a PASS."""
    if not verdicts:
        return INCONCLUSIVE
    if FAIL in verdicts:
        return FAIL
    if INCONCLUSIVE in verdicts:
        return INCONCLUSIVE
    return PASS


def probe_tcp(address: str, port: int, timeout: float) -> str:
    """Return one of the outcome constants above. Never raises."""
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


def validate_ports(ports: list[int]) -> str | None:
    """Return an error message if the requested port list is unusable."""
    for port in ports:
        if not 1 <= port <= 65535:
            return f"port {port} is out of range 1..65535"
    if PERMITTED_TRANSPORT_PORT in ports:
        return (
            f"port {PERMITTED_TRANSPORT_PORT} is the permitted WireGuard "
            f"{PERMITTED_TRANSPORT_PROTOCOL.upper()} transport port "
            "(contracts/compute-link.md C1a). This script probes TCP only and "
            "must not report on that port: a TCP result there would be read as "
            "a statement about the UDP transport. Verify the transport "
            "listener's scope origin-locally instead (tasks.md T066a)."
        )
    return None


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin-address", default=APPROVED_ORIGIN_ADDRESS)
    parser.add_argument("--ports", type=int, nargs="+", default=list(PROHIBITED_TCP_PORTS))
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument(
        "--confirm-off-campus",
        action="store_true",
        help="Confirm this process is running outside the university network",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.timeout <= 0:
        print("REFUSED: timeout must be positive", file=sys.stderr)
        return 2
    if not args.confirm_off_campus:
        print("REFUSED: add --confirm-off-campus before recording external evidence", file=sys.stderr)
        return 2
    if args.origin_address != APPROVED_ORIGIN_ADDRESS:
        print(
            f"REFUSED: only the approved origin address {APPROVED_ORIGIN_ADDRESS} may be probed",
            file=sys.stderr,
        )
        return 2
    port_error = validate_ports(args.ports)
    if port_error:
        print(f"REFUSED: {port_error}", file=sys.stderr)
        return 2

    print(
        f"PERMITTED (not probed): {PERMITTED_TRANSPORT_PROTOCOL}/"
        f"{PERMITTED_TRANSPORT_PORT} - the Option A WireGuard transport "
        "listener (contracts/compute-link.md C1a). Its existence and scope are "
        "not observable from here; origin-local evidence is required (T066a, SC-018)."
    )

    verdicts: list[str] = []
    for port in args.ports:
        outcome = probe_tcp(args.origin_address, port, args.timeout)
        verdict, why = classify_probe(outcome)
        verdicts.append(verdict)
        print(f"{verdict}: tcp/{port} - {why}")

    result = overall_verdict(verdicts)
    if result == FAIL:
        print(
            "FAIL: at least one prohibited TCP port accepted a connection; the "
            "origin exposes a direct Internet-facing listener",
            file=sys.stderr,
        )
        return 1
    if result == INCONCLUSIVE:
        print(
            "INCONCLUSIVE: no prohibited port accepted a connection, but at "
            "least one probe was silently dropped or unclassifiable. Failing "
            "closed - this run is not lockdown evidence. Pair it with the "
            "origin-local listener inventory (T062, T066a).",
            file=sys.stderr,
        )
        return 3
    print(
        "PASS (remote scope): every prohibited TCP port was unambiguously "
        "refused or reset. This corroborates but does not replace the "
        "origin-local listener inventory required for SC-018."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
