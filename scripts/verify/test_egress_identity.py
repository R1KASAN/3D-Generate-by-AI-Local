"""Verify the approved address is demonstrably in the production path
(feature-003 T053, FR-002a, FR-011e).

Two mutually exclusive methods, selected by --provider, per
specs/003-outbound-tunnel-entry/contracts/evidence-methods.md E1:

  --provider cloudflare   Reads the active connector's reported origin
                           address from Cloudflare's tunnel-connections
                           API (requires an API token with Tunnel:Read on
                           the account - never hardcode or log it).

  --provider zrok          zrok exposes no documented origin-IP interface,
                           so this method proves the two things that
                           together establish the requirement without
                           assuming one exists: (1) the zrok connector
                           process is running ON the approved origin
                           (checked locally on that host), and (2) the
                           origin's own outbound path currently presents
                           the approved address (an external egress-IP
                           check performed FROM the origin). This MUST be
                           run on the approved origin itself, not remotely.

Neither method binds the connector's source address - that decision stays
deferred until physical inspection confirms 161.200.90.4 is directly
bindable on the origin (contracts/evidence-methods.md E2).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _evidence import Check, overall_verdict, write_evidence  # noqa: E402

APPROVED_ORIGIN_ADDRESS = "161.200.90.4"


def _cloudflare_check(account_id: str, tunnel_id: str, api_token: str) -> Check:
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/cfd_tunnel/{tunnel_id}/connections"
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {api_token}"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            payload = json.loads(response.read())
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as exc:
        return Check("cloudflare-connections-api", f"request failed: {type(exc).__name__}", f"active connector reports origin_ip={APPROVED_ORIGIN_ADDRESS}", "BLOCKED")

    reported_ips: set[str] = set()
    if not isinstance(payload, dict) or payload.get("success") is not True:
        return Check("cloudflare-connections-api", "unsuccessful API response", "successful connections response", "BLOCKED")
    groups = payload.get("result")
    if not isinstance(groups, list):
        return Check("cloudflare-connections-api", "unrecognized response", "connector list", "BLOCKED")
    # Inspect only documented connection records, not unrelated metadata.
    incomplete = False
    for group in groups:
        if not isinstance(group, dict) or not isinstance(group.get("conns"), list):
            incomplete = True
            continue
        for connection in group["conns"]:
            if not isinstance(connection, dict):
                incomplete = True
                continue
            if connection.get("is_pending_reconnect") is True:
                continue
            address = connection.get("origin_ip")
            if not isinstance(address, str) or not address:
                incomplete = True
            else:
                reported_ips.add(address)
    matched = not incomplete and reported_ips == {APPROVED_ORIGIN_ADDRESS}
    observed = f"reported origin_ip values: {sorted(reported_ips)}" if reported_ips else "no origin_ip field found in response"
    return Check("cloudflare-connections-api", observed, f"origin_ip={APPROVED_ORIGIN_ADDRESS}", "PASS" if matched else "FAIL")


def _zrok_connector_on_origin_check(process_name_hint: str) -> Check:
    """Least invasive local check: is a zrok connector process actually
    running on this host? Run this ON the approved origin."""
    try:
        if shutil.which("pgrep"):
            proc = subprocess.run(["pgrep", "-x", process_name_hint], capture_output=True, text=True, timeout=10)
            running = proc.returncode == 0 and bool(proc.stdout.strip())
            detail = f"pgrep matched pid(s): {proc.stdout.strip()}" if running else "pgrep found no matching process"
        else:
            proc = subprocess.run(
                ["powershell", "-NoProfile", "-Command", f"[bool](Get-Process -Name '{process_name_hint}' -ErrorAction SilentlyContinue)"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            running = proc.stdout.strip().lower() == "true"
            detail = "matched a running process" if running else "no matching process found"
    except Exception as exc:  # noqa: BLE001
        return Check("zrok-connector-on-origin", f"{type(exc).__name__}", "zrok connector process running on this host", "BLOCKED")
    return Check("zrok-connector-on-origin", detail, "zrok connector process running on this host", "PASS" if running else "FAIL")


def _egress_address_check() -> Check:
    """External egress-IP check performed FROM the origin. Uses a plain
    HTTPS GET to an external echo endpoint - deliberately not a Cloudflare
    or zrok API, since this check must work regardless of which provider
    is under test."""
    try:
        with urllib.request.urlopen("https://api.ipify.org", timeout=10) as response:
            observed_ip = response.read().decode("utf-8").strip()
    except (urllib.error.URLError, OSError) as exc:
        return Check("origin-egress-address", f"request failed: {type(exc).__name__}", f"egress address is {APPROVED_ORIGIN_ADDRESS}", "BLOCKED")
    if not re.match(r"^\d{1,3}(\.\d{1,3}){3}$", observed_ip):
        return Check("origin-egress-address", f"unexpected response: {observed_ip!r}", f"egress address is {APPROVED_ORIGIN_ADDRESS}", "BLOCKED")
    matched = observed_ip == APPROVED_ORIGIN_ADDRESS
    return Check("origin-egress-address", f"observed {observed_ip}", f"egress address is {APPROVED_ORIGIN_ADDRESS}", "PASS" if matched else "FAIL")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=["cloudflare", "zrok"], required=True)
    parser.add_argument("--cloudflare-account-id", default=None)
    parser.add_argument("--cloudflare-tunnel-id", default=None)
    parser.add_argument("--cloudflare-api-token", default=os.environ.get("CLOUDFLARE_API_TOKEN"), help="Prefer CLOUDFLARE_API_TOKEN environment variable to avoid command-line exposure")
    parser.add_argument("--zrok-process-name", choices=["zrok"], default="zrok", help="Exact connector executable name")
    parser.add_argument("--confirm-run-on-origin", action="store_true", help="Required for --provider zrok: attests this script is running on the approved origin itself")
    parser.add_argument("--evidence", type=Path, default=Path("evidence/public-deployment/egress-identity.md"))
    args = parser.parse_args()

    checks: list[Check] = []
    if args.provider == "cloudflare":
        if not all((args.cloudflare_account_id, args.cloudflare_tunnel_id, args.cloudflare_api_token)):
            checks.append(Check("cloudflare-inputs", "account id/tunnel id/api token not all supplied", "all three provided", "BLOCKED"))
        else:
            checks.append(_cloudflare_check(args.cloudflare_account_id, args.cloudflare_tunnel_id, args.cloudflare_api_token))
    else:
        if not args.confirm_run_on_origin:
            checks.append(Check("vantage-point", "--confirm-run-on-origin was not supplied", "run on the approved origin itself, not remotely", "BLOCKED"))
        else:
            checks.append(_zrok_connector_on_origin_check(args.zrok_process_name))
            checks.append(_egress_address_check())

    verdict = overall_verdict(checks)
    write_evidence(
        args.evidence,
        "Origin Egress Identity Evidence",
        "T053",
        [f"- Provider: {args.provider}"],
        checks,
        verdict,
        footnote="Proves FR-002a/FR-011e: the approved address is demonstrably in the production path. Does not bind the connector's source address - that remains deferred pending physical inspection.",
    )
    print(f"{verdict}: egress-identity evidence written to {args.evidence}")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
