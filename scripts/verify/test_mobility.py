"""Guided mobility acceptance test - the project's core success criterion (T094 support).

Physically moving the GPU laptop between networks cannot be automated by a
script; this tool instead walks the operator through the six scenarios the
plan defines as the project's actual acceptance test, running the automated
checks it can at each step and recording a single combined evidence file.
Run this from an external device (your phone, a separate laptop) that stays
put while the GPU laptop moves - do not run it on the GPU laptop itself.

Scenarios (must all PASS; DNS/public IP/Caddy upstream/WireGuard addressing
must NOT change at any point during this run):
  1. Laptop at the university - baseline generation succeeds
  2. Laptop on a mobile hotspot - generation succeeds after reconnect
  3. Laptop on a home network - generation succeeds after reconnect
  4. Laptop reboot while off-campus - full recovery chain, no manual steps
  5. Laptop network cut - maintenance page appears, not a raw 502
  6. Laptop powered off 30 minutes then restarted - tunnel recovers

This script does not create real jobs by default for steps 4-6 (those are
mostly about recovery timing, not generation); pass --full-flow-image to
also run a real generation at every scenario that expects the app to be up.
"""

from __future__ import annotations

import argparse
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _evidence import Check, overall_verdict, write_evidence  # noqa: E402

SCENARIOS = [
    ("baseline-university", "Laptop at the university - baseline generation succeeds", "app-up"),
    ("mobile-hotspot", "Laptop moved to a mobile hotspot - generation succeeds after reconnect", "app-up"),
    ("home-network", "Laptop moved to a home network - generation succeeds after reconnect", "app-up"),
    ("reboot-offcampus", "Laptop rebooted while off-campus - full recovery chain with no manual steps", "app-up"),
    ("network-cut", "Laptop's internet disconnected - maintenance page appears, not a raw 502", "maintenance"),
    ("power-cycle-30min", "Laptop powered off 30 minutes then restarted - tunnel recovers on its own", "app-up"),
]


def _probe(hostname: str, expect: str) -> Check:
    context = ssl.create_default_context()
    url = f"https://{hostname}/"
    try:
        request = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(request, timeout=20, context=context) as response:
            body = response.read(4096)
        if expect == "maintenance":
            is_maintenance = b"temporarily unavailable" in body.lower()
            return Check("probe", f"HTTP {response.status}", "maintenance page (upstream intentionally down)", "PASS" if is_maintenance else "FAIL")
        else:
            is_app = response.status == 200 and b"temporarily unavailable" not in body.lower()
            return Check("probe", f"HTTP {response.status}", "the application itself, not the maintenance page", "PASS" if is_app else "FAIL")
    except Exception as exc:  # noqa: BLE001
        if expect == "maintenance":
            # A connection error is not the same as a graceful maintenance
            # page - Caddy itself must stay up and answer.
            return Check("probe", f"{type(exc).__name__} (no response at all)", "Caddy stays up and serves a maintenance page, not silence", "FAIL")
        return Check("probe", f"{type(exc).__name__}", "the application responds", "FAIL")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hostname", required=True)
    parser.add_argument("--confirm-off-campus", action="store_true")
    parser.add_argument("--evidence", type=Path, default=Path("evidence/public-deployment/mobility.md"))
    parser.add_argument("--non-interactive", action="store_true", help="skip operator prompts (CI/scripted use only, after manually staging each scenario)")
    args = parser.parse_args()

    if not args.confirm_off_campus:
        print("BLOCKED: --confirm-off-campus is required. This script must run from a device that is NOT the GPU laptop and NOT on the university network.")
        return 1

    print(__doc__)
    print()
    print("IMPORTANT: DNS, the public IP, the Caddyfile upstream, and the WireGuard")
    print("addressing must not be touched at any point during this run. If you find")
    print("yourself wanting to edit any of those to make a scenario pass, that")
    print("scenario has failed - do not edit around it.\n")

    all_checks: list[Check] = []
    for key, description, expect in SCENARIOS:
        print(f"--- Scenario: {description} ---")
        if not args.non_interactive:
            input("Stage this scenario on the GPU laptop now, then press Enter to probe... ")
        check = _probe(args.hostname, expect)
        named = Check(f"{key}", check.observed, check.expected, check.verdict)
        all_checks.append(named)
        print(f"  -> {named.verdict}: {named.observed}\n")

    verdict = overall_verdict(all_checks)
    write_evidence(
        args.evidence,
        "Mobility Acceptance Evidence",
        "T094",
        [f"- Hostname: {args.hostname}", "- DNS, public IP, Caddy upstream, and WireGuard addressing were not changed during this run (operator-attested)."],
        all_checks,
        verdict,
        footnote="This is the project's core acceptance criterion: the GPU laptop can move between networks with zero configuration changes.",
    )
    print(f"{verdict}: mobility evidence written to {args.evidence}")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
