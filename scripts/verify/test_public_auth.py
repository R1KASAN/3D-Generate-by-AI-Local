"""Verify per-job token enforcement over the public HTTPS entry (T091).

Requires two real jobs already created against the public endpoint. Tokens
are supplied through environment variables only, mirroring
scripts/verify/run_lan_boundary.py - they are never printed, logged, or
written to the evidence file. Also optionally greps a local copy of the
Caddy access log for the literal token values to confirm the log-redaction
filter (tests/security/test_caddy_contract.py) actually worked in
production, not just in the static Caddyfile.
"""

from __future__ import annotations

import argparse
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _evidence import Check, overall_verdict, write_evidence  # noqa: E402


def _request(url: str, headers: dict[str, str] | None = None) -> tuple[int, bytes]:
    request = urllib.request.Request(url, headers=headers or {}, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def _uniform_404(base: str, job_id: str, header: dict[str, str]) -> tuple[bool, str]:
    statuses = []
    for suffix in ("", "/model", "/download"):
        status, _ = _request(f"{base}/api/v1/jobs/{job_id}{suffix}", header)
        statuses.append(status)
    return all(s == 404 for s in statuses), ",".join(str(s) for s in statuses)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hostname", required=True)
    parser.add_argument("--confirm-off-campus", action="store_true")
    parser.add_argument("--caddy-log", type=Path, default=None, help="local copy of the edge's Caddy access log, to grep for leaked tokens")
    parser.add_argument("--evidence", type=Path, default=Path("evidence/public-deployment/auth.md"))
    args = parser.parse_args()
    base = f"https://{args.hostname}"

    if not args.confirm_off_campus:
        checks = [Check("vantage-point", "--confirm-off-campus was not supplied", "run from outside the university network", "BLOCKED")]
        write_evidence(args.evidence, "Public Auth Boundary Evidence", "T091", [f"- Hostname: {args.hostname}"], checks, "BLOCKED")
        print(f"BLOCKED: auth evidence written to {args.evidence}")
        return 1

    checks = [Check("vantage-point", "operator attested off-campus", "run from outside the university network", "PASS")]

    job_a = os.environ.get("PUBLIC_JOB_A", "").strip()
    token_a = os.environ.get("PUBLIC_TOKEN_A", "").strip()
    job_b = os.environ.get("PUBLIC_JOB_B", "").strip()
    token_b = os.environ.get("PUBLIC_TOKEN_B", "").strip()

    if not all((job_a, token_a, job_b, token_b)):
        checks.append(Check("cross-job-denial", "PUBLIC_JOB_A/PUBLIC_TOKEN_A/PUBLIC_JOB_B/PUBLIC_TOKEN_B not all supplied", "two real jobs' ids/tokens provided via environment", "BLOCKED"))
    else:
        wrong_ok, wrong_statuses = _uniform_404(base, job_b, {"X-Job-Token": token_a})
        missing_ok, missing_statuses = _uniform_404(base, job_a, {})
        checks.append(Check("wrong-token-denial", f"statuses={wrong_statuses}", "uniform 404 across /{id}, /model, /download", "PASS" if wrong_ok else "FAIL"))
        checks.append(Check("missing-token-denial", f"statuses={missing_statuses}", "uniform 404 across /{id}, /model, /download", "PASS" if missing_ok else "FAIL"))

    if args.caddy_log and args.caddy_log.exists():
        log_text = args.caddy_log.read_text(encoding="utf-8", errors="ignore")
        leaked = any(t and t in log_text for t in (token_a, token_b))
        checks.append(Check("token-not-in-log", "leaked" if leaked else "not found", "token value never appears in the Caddy access log", "FAIL" if leaked else "PASS"))
    else:
        checks.append(Check("token-not-in-log", "--caddy-log not supplied or file missing", "token value never appears in the Caddy access log", "BLOCKED"))

    verdict = overall_verdict(checks)
    write_evidence(
        args.evidence,
        "Public Auth Boundary Evidence",
        "T091",
        [f"- Hostname: {args.hostname}"],
        checks,
        verdict,
        footnote="Job ids/tokens are read from PUBLIC_JOB_A/PUBLIC_TOKEN_A/PUBLIC_JOB_B/PUBLIC_TOKEN_B and never written to this file.",
    )
    print(f"{verdict}: auth evidence written to {args.evidence}")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
