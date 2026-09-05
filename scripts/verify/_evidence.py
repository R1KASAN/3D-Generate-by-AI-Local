"""Shared Check/evidence-writing helpers for the public-deployment verifiers
(feature-002 T025-T026 and T035). Mirrors the shape used by scripts/verify/test_lan_boundary.py
so evidence files stay consistent across the LAN and public-deployment
verification suites.
"""

from __future__ import annotations

import datetime as dt
import ipaddress
import re
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
    if ":" in address:
        return "[IPv6 masked]"
    return address


_IPV4_LITERAL = re.compile(r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])")
_IPV6_LITERAL = re.compile(r"(?<![\w:])[0-9a-fA-F:]*:[0-9a-fA-F:]+(?:%[\w]+)?(?![\w:])")
_CREDENTIAL = re.compile(r"(?i)\b(X-Job-Token|Authorization|Cookie|job_token|api_token)\s*[:=]\s*[^\r\n,|]+")


def mask_text(value: str) -> str:
    """Mask every standalone IPv4 literal before it reaches evidence."""
    def ipv6(match: re.Match[str]) -> str:
        try:
            ipaddress.IPv6Address(match.group())
        except ValueError:
            return match.group()
        return "[IPv6 masked]"

    value = _CREDENTIAL.sub(lambda m: m.group(1) + "=[REDACTED]", value)
    value = _IPV6_LITERAL.sub(ipv6, value)
    return _IPV4_LITERAL.sub(lambda match: mask_ip(match.group(0)), value)


def write_evidence(
    path: Path,
    title: str,
    task_id: str,
    context_lines: list[str],
    checks: list[Check],
    verdict: str,
    footnote: str = "",
) -> None:
    lines = [f"# {mask_text(title)} ({mask_text(task_id)})", ""]
    lines.append(f"- Date/time (UTC): {dt.datetime.now(dt.UTC).isoformat()}")
    lines.extend(mask_text(line) for line in context_lines)
    lines.append("- Credentials, capability tokens, and full public IP addresses are omitted.")
    lines.append("")
    lines.append("| Check | Observed | Expected | Verdict |")
    lines.append("|---|---|---|---|")
    for check in checks:
        observed = mask_text(check.observed).replace("|", "\\|")
        expected = mask_text(check.expected).replace("|", "\\|")
        name = mask_text(check.name).replace("|", "\\|")
        lines.append(f"| {name} | {observed} | {expected} | **{check.verdict}** |")
    lines.append("")
    if footnote:
        lines.append(f"- {mask_text(footnote)}")
    lines.append(f"- Overall verdict: **{verdict}**")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
