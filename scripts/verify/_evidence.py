"""Shared Check/evidence-writing helpers for the public-deployment verifiers
(T090-T094). Mirrors the shape used by scripts/verify/test_lan_boundary.py
so evidence files stay consistent across the LAN and public-deployment
verification suites.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Check:
    name: str
    observed: str
    expected: str
    verdict: str  # "PASS" | "FAIL" | "BLOCKED"


def overall_verdict(checks: list[Check]) -> str:
    verdicts = {c.verdict for c in checks}
    if "FAIL" in verdicts:
        return "FAIL"
    if "BLOCKED" in verdicts:
        return "BLOCKED"
    return "PASS"


def mask_ip(address: str) -> str:
    """Mask the last IPv4 octet: 161.200.90.4 -> 161.200.90.x. Never write a
    full public deployment IP address to an evidence file."""
    parts = address.split(".")
    if len(parts) == 4:
        return ".".join(parts[:3] + ["x"])
    return address


def write_evidence(
    path: Path,
    title: str,
    task_id: str,
    context_lines: list[str],
    checks: list[Check],
    verdict: str,
    footnote: str = "",
) -> None:
    lines = [f"# {title} ({task_id})", ""]
    lines.append(f"- Date/time (UTC): {dt.datetime.now(dt.UTC).isoformat()}")
    lines.extend(context_lines)
    lines.append("- Credentials, capability tokens, and full public IP addresses are omitted.")
    lines.append("")
    lines.append("| Check | Observed | Expected | Verdict |")
    lines.append("|---|---|---|---|")
    for check in checks:
        observed = check.observed.replace("|", "\\|")
        expected = check.expected.replace("|", "\\|")
        lines.append(f"| {check.name} | {observed} | {expected} | **{check.verdict}** |")
    lines.append("")
    if footnote:
        lines.append(f"- {footnote}")
    lines.append(f"- Overall verdict: **{verdict}**")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
