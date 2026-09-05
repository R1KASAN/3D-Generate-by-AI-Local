"""Verify per-job token enforcement over the public HTTPS entry (feature-002 T026).

Requires two real jobs already created against the public endpoint. Tokens
are supplied through environment variables only, mirroring
scripts/verify/run_lan_boundary.py - they are never printed, logged, or
written to the evidence file. It checks the origin access log, origin error
log, and application logs when those local copies are supplied, because the
no-token guarantee covers every project-controlled log and not only the Caddy
access log.
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
    parser.add_argument("--caddy-log", type=Path, default=None, help="local copy of the origin Caddy access log")
    parser.add_argument("--caddy-error-log", type=Path, default=None, help="local copy of the origin Caddy error log")
    parser.add_argument("--application-log", type=Path, action="append", default=[], help="local application log copy; may be supplied more than once")
    parser.add_argument("--evidence", type=Path, default=Path("evidence/public-deployment/auth.md"))
    args = parser.parse_args()
    base = f"https://{args.hostname}"

    if not args.confirm_off_campus:
        checks = [Check("vantage-point", "--confirm-off-campus was not supplied", "run from outside the university network", "BLOCKED")]
        write_evidence(args.evidence, "Public Auth Boundary Evidence", "T026", [f"- Hostname: {args.hostname}"], checks, "BLOCKED")
        print(f"BLOCKED: auth evidence written to {args.evidence}")
        return 1

    checks = [Check("vantage-point", "operator attested off-campus", "run from outside the university network", "PASS")]

    job_a = os.environ.get("PUBLIC_JOB_A", "").strip()
    token_a = os.environ.get("PUBLIC_TOKEN_A", "").strip()
    job_b = os.environ.get("PUBLIC_JOB_B", "").strip()
    token_b = os.environ.get("PUBLIC_TOKEN_B", "").strip()
    # A token from a job whose retention window has elapsed (or one the
    # operator has otherwise invalidated). Distinct from "wrong" (belongs to
    # a different live job) and "missing" (no token at all) - SC-010
    # requires all three, plus cross-job, to be indistinguishable.
    job_expired = os.environ.get("PUBLIC_JOB_EXPIRED", "").strip()
    token_expired = os.environ.get("PUBLIC_TOKEN_EXPIRED", "").strip()

    if not all((job_a, token_a, job_b, token_b)):
        checks.append(Check("cross-job-denial", "PUBLIC_JOB_A/PUBLIC_TOKEN_A/PUBLIC_JOB_B/PUBLIC_TOKEN_B not all supplied", "two real jobs' ids/tokens provided via environment", "BLOCKED"))
    else:
        wrong_ok, wrong_statuses = _uniform_404(base, job_b, {"X-Job-Token": token_a})
        missing_ok, missing_statuses = _uniform_404(base, job_a, {})
        checks.append(Check("wrong-token-denial", f"statuses={wrong_statuses}", "uniform 404 across /{id}, /model, /download", "PASS" if wrong_ok else "FAIL"))
        checks.append(Check("missing-token-denial", f"statuses={missing_statuses}", "uniform 404 across /{id}, /model, /download", "PASS" if missing_ok else "FAIL"))

    if not all((job_expired, token_expired)):
        checks.append(Check("expired-token-denial", "PUBLIC_JOB_EXPIRED/PUBLIC_TOKEN_EXPIRED not supplied", "an expired job's id/token provided via environment", "BLOCKED"))
    else:
        expired_ok, expired_statuses = _uniform_404(base, job_expired, {"X-Job-Token": token_expired})
        checks.append(Check("expired-token-denial", f"statuses={expired_statuses}", "uniform 404 across /{id}, /model, /download, same shape as missing/wrong/cross-job", "PASS" if expired_ok else "FAIL"))

    log_paths = [
        ("origin-access-log", args.caddy_log),
        ("origin-error-log", args.caddy_error_log),
        *[(f"application-log-{index}", path) for index, path in enumerate(args.application_log, start=1)],
    ]
    if not all((job_a, token_a, job_b, token_b)):
        checks.append(Check("project-controlled-logs", "tokens not supplied; log search cannot run", "all project-controlled logs searched for known token values", "BLOCKED"))
    elif not log_paths:
        checks.append(Check("project-controlled-logs", "no origin/application log paths supplied", "origin access/error and application logs searched", "BLOCKED"))
    else:
        for label, path in log_paths:
            if path is None or not path.exists():
                checks.append(Check(label, "file missing", "log copy supplied and contains no token value", "BLOCKED"))
                continue
            log_text = path.read_text(encoding="utf-8", errors="ignore")
            candidate_tokens = [t for t in (token_a, token_b, token_expired) if t]
            leaked = any(token in log_text for token in candidate_tokens)
            checks.append(Check(label, "token found" if leaked else "token not found", "no known token value", "FAIL" if leaked else "PASS"))

    verdict = overall_verdict(checks)
    write_evidence(
        args.evidence,
        "Public Auth Boundary Evidence",
        "T026",
        [f"- Hostname: {args.hostname}"],
        checks,
        verdict,
        footnote="Job ids/tokens are read from PUBLIC_JOB_A/PUBLIC_TOKEN_A/PUBLIC_JOB_B/PUBLIC_TOKEN_B and never written to this file.",
    )
    print(f"{verdict}: auth evidence written to {args.evidence}")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
