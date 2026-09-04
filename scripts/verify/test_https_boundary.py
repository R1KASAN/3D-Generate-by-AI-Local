"""Verify the public HTTPS entry from outside the university network (T090).

Must be run from a genuinely external vantage point (mobile data, home
network, or an off-campus VPS) - a probe from inside the university network
is not evidence that the border firewall and public routing actually work,
the same way scripts/verify/test_lan_boundary.py refuses a server-local
probe as LAN evidence. Pass --confirm-off-campus to attest this; without it
the run is recorded as BLOCKED, not PASS.
"""

from __future__ import annotations

import argparse
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _evidence import Check, overall_verdict, write_evidence  # noqa: E402


def _https_check(hostname: str) -> Check:
    context = ssl.create_default_context()  # validates chain + hostname
    url = f"https://{hostname}/"
    try:
        request = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(request, timeout=15, context=context) as response:
            ok = 200 <= response.status < 300
            return Check("https-entry", f"HTTP {response.status}, valid certificate chain", "2xx with a valid, trusted certificate", "PASS" if ok else "FAIL")
    except urllib.error.HTTPError as exc:
        return Check("https-entry", f"HTTP {exc.code}", "2xx with a valid, trusted certificate", "FAIL")
    except ssl.SSLCertVerificationError as exc:
        return Check("https-entry", f"certificate verification failed: {exc.verify_message}", "a valid, trusted certificate", "FAIL")
    except Exception as exc:  # noqa: BLE001
        return Check("https-entry", f"request failed with {type(exc).__name__}", "2xx with a valid, trusted certificate", "BLOCKED")


def _http_redirect_check(hostname: str) -> Check:
    url = f"http://{hostname}/"
    try:
        request = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(request, timeout=15) as response:
            # urllib follows redirects by default; inspect the final URL.
            final_url = response.geturl()
            ok = final_url.startswith("https://")
            return Check("http-redirect", f"final URL: {final_url}", "redirects to https://", "PASS" if ok else "FAIL")
    except Exception as exc:  # noqa: BLE001
        return Check("http-redirect", f"request failed with {type(exc).__name__}", "redirects to https://", "BLOCKED")


def _bare_ip_check(public_ip: str) -> Check:
    """A request to the bare public IP with no SNI/matching Host must not
    serve the application (the Caddyfile's catch-all block)."""
    context = ssl._create_unverified_context()  # noqa: SLF001 - deliberately not validating a self-signed catch-all cert
    try:
        request = urllib.request.Request(f"https://{public_ip}/", method="GET")
        with urllib.request.urlopen(request, timeout=10, context=context) as response:
            body = response.read(200)
            served_app = b"Local3D" in body or response.status == 200 and b"<!doctype" in body.lower()
            return Check(
                "bare-ip-not-app",
                f"HTTP {response.status}",
                "does not serve the application (404 or unrelated content)",
                "FAIL" if served_app else "PASS",
            )
    except Exception as exc:  # noqa: BLE001
        # A refused/reset/timeout connection, or a 404, all count as "did not serve the app".
        return Check("bare-ip-not-app", f"{type(exc).__name__} (no application served)", "does not serve the application", "PASS")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hostname", required=True, help="approved public hostname")
    parser.add_argument("--public-ip", required=True, help="approved edge public IP (161.200.90.4)")
    parser.add_argument("--confirm-off-campus", action="store_true", help="attest this run is from outside the university network")
    parser.add_argument("--evidence", type=Path, default=Path("evidence/public-deployment/tls.md"))
    args = parser.parse_args()

    if args.public_ip != "161.200.90.4":
        print("BLOCKED: --public-ip must be exactly 161.200.90.4; refusing to probe any other address.")
        return 1

    if not args.confirm_off_campus:
        checks = [Check("vantage-point", "--confirm-off-campus was not supplied", "run from a genuinely external network (mobile data/home/off-campus VPS)", "BLOCKED")]
        verdict = "BLOCKED"
    else:
        checks = [
            Check("vantage-point", "operator attested off-campus", "run from a genuinely external network", "PASS"),
            _https_check(args.hostname),
            _http_redirect_check(args.hostname),
            _bare_ip_check(args.public_ip),
        ]
        verdict = overall_verdict(checks)

    from _evidence import mask_ip  # noqa: E402

    write_evidence(
        args.evidence,
        "HTTPS Boundary Evidence",
        "T090",
        [f"- Public hostname: {args.hostname}", f"- Edge address (masked): {mask_ip(args.public_ip)}"],
        checks,
        verdict,
        footnote="A PASS requires execution from a genuinely external vantage point; an unattested or on-campus probe is BLOCKED.",
    )
    print(f"{verdict}: HTTPS boundary evidence written to {args.evidence}")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
