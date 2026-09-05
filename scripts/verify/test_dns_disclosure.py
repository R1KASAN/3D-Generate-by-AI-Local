"""Verify that public DNS does not disclose the origin address (feature 003,
FR-005, FR-011b, SC-004).

Run this from an external network with the final public hostname and
``--confirm-off-campus``. A missing DNS record is a failure, not a pass: the
public entry must exist and resolve through the provider before acceptance.

Feature 003 additionally requires that the resolved address is
provider-facing routing information, not merely "any public address" - an
`A` record pointing anywhere other than the Cloudflare edge (including a
different hosting provider entirely) would still technically hide the
origin's own address while failing FR-011b's actual intent. This is checked
by fetching Cloudflare's own published IP ranges (the same source
deploy/firewall/cloudflare-ranges.ps1 uses) and confirming every resolved
address falls inside them; a failed fetch degrades this one check to
BLOCKED rather than failing the whole script, since it depends on network
access to Cloudflare's own range-publishing endpoint.
"""

from __future__ import annotations

import argparse
import ipaddress
import socket
import sys
import urllib.error
import urllib.request


APPROVED_ORIGIN_ADDRESS = "161.200.90.4"
CLOUDFLARE_RANGE_URLS = ("https://www.cloudflare.com/ips-v4", "https://www.cloudflare.com/ips-v6")


def _fetch_cloudflare_ranges() -> list[ipaddress.IPv4Network | ipaddress.IPv6Network] | None:
    ranges: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
    try:
        for url in CLOUDFLARE_RANGE_URLS:
            with urllib.request.urlopen(url, timeout=10) as response:
                text = response.read().decode("utf-8")
            for line in text.splitlines():
                line = line.strip()
                if line:
                    ranges.append(ipaddress.ip_network(line))
    except (urllib.error.URLError, ValueError, OSError):
        return None
    return ranges or None


def _address_in_any_range(address: str, ranges: list[ipaddress.IPv4Network | ipaddress.IPv6Network]) -> bool:
    ip = ipaddress.ip_address(address)
    return any(ip in network for network in ranges)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hostname", required=True)
    parser.add_argument("--origin-address", default=APPROVED_ORIGIN_ADDRESS)
    parser.add_argument(
        "--confirm-off-campus",
        action="store_true",
        help="Confirm this process is running outside the university network",
    )
    return parser.parse_args()


def _resolve(hostname: str) -> set[str]:
    return {
        result[4][0]
        for result in socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)
    }


def main() -> int:
    args = _parse_args()
    if not args.confirm_off_campus:
        print("REFUSED: add --confirm-off-campus before recording external evidence", file=sys.stderr)
        return 2
    if args.origin_address != APPROVED_ORIGIN_ADDRESS:
        print(
            f"REFUSED: only the approved origin address {APPROVED_ORIGIN_ADDRESS} may be checked",
            file=sys.stderr,
        )
        return 2
    try:
        answers = _resolve(args.hostname)
    except socket.gaierror as exc:
        print(f"FAIL: hostname did not resolve ({exc})", file=sys.stderr)
        return 1
    if not answers:
        print("FAIL: hostname returned no address answers", file=sys.stderr)
        return 1
    if args.origin_address in answers:
        print("FAIL: public DNS discloses the origin address", file=sys.stderr)
        return 1
    non_public = sorted(answer for answer in answers if not ipaddress.ip_address(answer).is_global)
    if non_public:
        print("FAIL: public DNS returned a non-public address", file=sys.stderr)
        return 1

    ranges = _fetch_cloudflare_ranges()
    if ranges is None:
        print("BLOCKED: could not fetch Cloudflare's published IP ranges - cannot confirm resolved addresses are provider-facing (network-dependent; rerun with connectivity to cloudflare.com)")
        return 2
    else:
        not_cloudflare = sorted(a for a in answers if not _address_in_any_range(a, ranges))
        if not_cloudflare:
            print(f"FAIL: {len(not_cloudflare)} resolved address(es) are not within Cloudflare's published ranges - DNS is not routing through the approved provider edge (FR-011b)", file=sys.stderr)
            return 1
        print(f"PASS: all {len(answers)} resolved address(es) fall within Cloudflare's published ranges")

    print(f"PASS: {args.hostname} resolved to {len(answers)} public address answer(s) without the origin")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
