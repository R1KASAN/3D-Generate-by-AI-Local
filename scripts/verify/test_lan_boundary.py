"""Verify the Phase 10 LAN entry path from a genuinely separate client.

This script intentionally refuses to treat a server-local probe as LAN
evidence. Run it on the second device with the server's private LAN address.
Job IDs and tokens are supplied through environment variables and are never
printed or written to the evidence file.
"""

from __future__ import annotations

import argparse
import datetime as dt
import ipaddress
import os
import socket
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Check:
    name: str
    observed: str
    expected: str
    verdict: str


def _local_addresses() -> set[str]:
    addresses: set[str] = {"127.0.0.1"}
    try:
        hostname = socket.gethostname()
        addresses.update(item[4][0] for item in socket.getaddrinfo(hostname, None, socket.AF_INET))
    except OSError:
        pass
    return addresses


def _request(url: str, *, headers: dict[str, str] | None = None) -> tuple[int, bytes]:
    request = urllib.request.Request(url, headers=headers or {}, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def _port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=3):
            return True
    except OSError:
        return False


def _safe_error(exc: BaseException) -> str:
    if isinstance(exc, (urllib.error.URLError, TimeoutError, OSError)):
        return type(exc).__name__
    return type(exc).__name__


def run(args: argparse.Namespace) -> tuple[list[Check], str]:
    checks: list[Check] = []
    server_ip = ipaddress.ip_address(args.server_host)
    client_label = args.client_label.strip()

    if not client_label:
        checks.append(
            Check(
                "second-client-identity",
                "no --client-label supplied; this invocation cannot prove a second device",
                "named client device is separate from the Windows server",
                "BLOCKED",
            )
        )
        return checks, "BLOCKED"
    if args.server_host in _local_addresses() or server_ip.is_loopback:
        checks.append(
            Check(
                "second-client-identity",
                "the target server address resolves to this execution host",
                "script runs on a separate LAN device, not the server",
                "BLOCKED",
            )
        )
        return checks, "BLOCKED"
    checks.append(
        Check(
            "second-client-identity",
            f"client={client_label}; server={args.server_host}",
            "script runs on a separate LAN device",
            "PASS",
        )
    )

    entry_base = args.entry_url.rstrip("/")
    try:
        entry_status, _ = _request(entry_base + "/")
        entry_pass = 200 <= entry_status < 300
        checks.append(
            Check(
                "approved-entry",
                f"HTTP {entry_status}",
                "approved LAN entry path returns 2xx",
                "PASS" if entry_pass else "FAIL",
            )
        )
    except Exception as exc:
        checks.append(
            Check(
                "approved-entry",
                f"request failed with {_safe_error(exc)}",
                "approved LAN entry path returns 2xx",
                "BLOCKED",
            )
        )

    for port in (8000, 8188):
        open_state = _port_open(args.server_host, port)
        checks.append(
            Check(
                f"internal-port-{port}",
                "reachable" if open_state else "connection refused/blocked",
                f"{args.server_host}:{port} is unreachable from the LAN client",
                "FAIL" if open_state else "PASS",
            )
        )

    job_a = os.environ.get("LAN_JOB_A", "").strip()
    token_a = os.environ.get("LAN_TOKEN_A", "").strip()
    job_b = os.environ.get("LAN_JOB_B", "").strip()
    token_b = os.environ.get("LAN_TOKEN_B", "").strip()
    if not all((job_a, token_a, job_b, token_b)):
        checks.append(
            Check(
                "cross-job-denial",
                "LAN_JOB_A/LAN_TOKEN_A/LAN_JOB_B/LAN_TOKEN_B are not all supplied",
                "wrong-job token receives the same 404 response for both jobs",
                "BLOCKED",
            )
        )
    else:
        try:
            first_status, _ = _request(
                f"{entry_base}/api/v1/jobs/{job_b}", headers={"X-Job-Token": token_a}
            )
            second_status, _ = _request(
                f"{entry_base}/api/v1/jobs/{job_a}", headers={"X-Job-Token": token_b}
            )
            denial_pass = first_status == 404 and second_status == 404
            checks.append(
                Check(
                    "cross-job-denial",
                    f"wrong-token responses={first_status},{second_status}",
                    "wrong-job token receives uniform 404 responses",
                    "PASS" if denial_pass else "FAIL",
                )
            )
        except Exception as exc:
            checks.append(
                Check(
                    "cross-job-denial",
                    f"request failed with {_safe_error(exc)}",
                    "wrong-job token receives uniform 404 responses",
                    "BLOCKED",
                )
            )

    verdicts = {check.verdict for check in checks}
    overall = "FAIL" if "FAIL" in verdicts else "BLOCKED" if "BLOCKED" in verdicts else "PASS"
    return checks, overall


def write_evidence(path: Path, args: argparse.Namespace, checks: list[Check], verdict: str) -> None:
    lines = [
        "# LAN Boundary Evidence (T083)",
        "",
        f"- Date/time (UTC): {dt.datetime.now(dt.UTC).isoformat()}",
        f"- Client label: {args.client_label or 'not supplied'}",
        f"- Server LAN address: {args.server_host}",
        f"- Approved entry path: {args.entry_url}",
        "- Credentials, capability tokens, uploaded content, and private traces are omitted.",
        "",
        "| Check | Observed | Expected | Verdict |",
        "|---|---|---|---|",
    ]
    for check in checks:
        observed = check.observed.replace("|", "\\|")
        expected = check.expected.replace("|", "\\|")
        lines.append(f"| {check.name} | {observed} | {expected} | **{check.verdict}** |")
    lines += [
        "",
        "- A PASS requires execution from a separate LAN device; a server-local or missing-client probe is BLOCKED.",
        f"- Overall verdict: **{verdict}**",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server-host", default=os.environ.get("LAN_SERVER_HOST", ""))
    parser.add_argument("--entry-url", default=os.environ.get("LAN_ENTRY_URL", ""))
    parser.add_argument("--client-label", default=os.environ.get("LAN_CLIENT_LABEL", ""))
    parser.add_argument(
        "--evidence",
        type=Path,
        default=Path("evidence/lan/isolation-and-ports.md"),
    )
    args = parser.parse_args()
    if not args.server_host or not args.entry_url:
        checks = [
            Check(
                "configuration",
                "--server-host and --entry-url are required",
                "server LAN address and approved entry path supplied by the operator",
                "BLOCKED",
            )
        ]
        write_evidence(args.evidence, args, checks, "BLOCKED")
        print(f"BLOCKED: LAN evidence written to {args.evidence}")
        return 1
    try:
        ipaddress.ip_address(args.server_host)
    except ValueError:
        checks = [
            Check(
                "configuration",
                "--server-host is not a literal IP address",
                "literal private LAN server address",
                "FAIL",
            )
        ]
        write_evidence(args.evidence, args, checks, "FAIL")
        print(f"FAIL: LAN evidence written to {args.evidence}")
        return 1
    checks, verdict = run(args)
    write_evidence(args.evidence, args, checks, verdict)
    print(f"{verdict}: LAN evidence written to {args.evidence}")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
