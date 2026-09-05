"""Verify every entry in the recorded cost boundary is zero-cost, requires
no mandatory payment card, and enables no paid fallback (feature-003 T041,
SC-005).

This is a static check against a structured cost record - it does not
touch any provider account. The record itself
(evidence/public-deployment/cost-boundary.md) must be produced by an
operator reviewing the actual provider plans in use; this script only
proves that record, once written, actually says what SC-005 requires
rather than silently drifting.

The cost record is expected as JSON (see --cost-record) with one entry per
introduced dependency:

    [
      {"dependency": "Cloudflare Tunnel (free plan)",
       "recurring_price_usd": 0,
       "payment_card_required": false,
       "paid_fallback_enabled": false},
      ...
    ]

A companion Markdown evidence file is also produced, matching the shape
used by the other scripts/verify/*.py checks.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _evidence import Check, overall_verdict, write_evidence  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cost-record", type=Path, required=True, help="JSON list of dependency cost entries")
    parser.add_argument("--evidence", type=Path, default=Path("evidence/public-deployment/cost-boundary-check.md"))
    args = parser.parse_args()

    if not args.cost_record.is_file():
        checks = [Check("cost-record-present", "file not found", "a JSON cost record supplied via --cost-record", "BLOCKED")]
        write_evidence(args.evidence, "Cost Boundary Verification", "T041", [], checks, "BLOCKED")
        print(f"BLOCKED: cost-boundary evidence written to {args.evidence}")
        return 1

    try:
        entries = json.loads(args.cost_record.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        checks = [Check("cost-record-valid-json", f"parse error: {exc}", "valid JSON list", "FAIL")]
        write_evidence(args.evidence, "Cost Boundary Verification", "T041", [], checks, "FAIL")
        print(f"FAIL: cost-boundary evidence written to {args.evidence}")
        return 1

    if not isinstance(entries, list) or not entries:
        checks = [Check("cost-record-non-empty", "empty or not a list", "at least one dependency entry", "FAIL")]
        write_evidence(args.evidence, "Cost Boundary Verification", "T041", [], checks, "FAIL")
        print(f"FAIL: cost-boundary evidence written to {args.evidence}")
        return 1

    checks: list[Check] = []
    required_fields = {"dependency", "recurring_price_usd", "payment_card_required", "paid_fallback_enabled"}
    for entry in entries:
        missing = required_fields - set(entry.keys()) if isinstance(entry, dict) else required_fields
        name = entry.get("dependency", "<unnamed>") if isinstance(entry, dict) else "<malformed entry>"
        if missing:
            checks.append(Check(f"{name}-shape", f"missing fields: {sorted(missing)}", "all required fields present", "FAIL"))
            continue
        price_ok = entry["recurring_price_usd"] == 0
        card_ok = entry["payment_card_required"] is False
        fallback_ok = entry["paid_fallback_enabled"] is False
        checks.append(Check(f"{name}-zero-cost", f"${entry['recurring_price_usd']}", "$0 recurring", "PASS" if price_ok else "FAIL"))
        checks.append(Check(f"{name}-no-card-required", str(entry["payment_card_required"]), "false", "PASS" if card_ok else "FAIL"))
        checks.append(Check(f"{name}-no-paid-fallback", str(entry["paid_fallback_enabled"]), "false", "PASS" if fallback_ok else "FAIL"))

    verdict = overall_verdict(checks)
    write_evidence(
        args.evidence,
        "Cost Boundary Verification",
        "T041",
        [f"- Dependencies checked: {len(entries)}"],
        checks,
        verdict,
        footnote="Verifies evidence/public-deployment/cost-boundary.md's claims (SC-005); does not itself query any provider account.",
    )
    print(f"{verdict}: cost-boundary evidence written to {args.evidence}")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
