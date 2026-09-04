"""Static contract tests for deploy/caddy/Caddyfile (T086).

These tests never start Caddy or touch the network - they parse the
Caddyfile text and assert the owner-approved public-entry policy is
encoded correctly, before any of it is ever deployed:

  - no site-wide login (basic_auth) - the approved policy is per-job
    capability tokens only, never a shared credential
  - the only upstream is the WireGuard tunnel address to the GPU laptop,
    never 0.0.0.0/::, never ComfyUI's port (:8188) directly
  - X-Job-Token is stripped from the access log, or it leaks in cleartext
  - a maintenance page is served when the upstream is unreachable
  - 161.200.90.3 never appears in deployment configuration (see the
    project's hard constraint: only .4 may ever be configured)

Run with: uv run --project apps/api pytest tests/security/test_caddy_contract.py
(or any Python 3.11+ with pytest installed; this file has no project
dependency beyond pytest and the standard library.)
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CADDYFILE = REPO_ROOT / "deploy" / "caddy" / "Caddyfile"

# Scope for the "never .3" check: deployment configuration and network
# scripts, not documentation or evidence, which must be free to explain
# why .3 is off-limits. See the plan's ⛔ constraint table.
FORBIDDEN_IP_SCAN_PATHS = [
    REPO_ROOT / "deploy",
    REPO_ROOT / "scripts" / "windows" / "start_web_service.ps1",
    REPO_ROOT / "scripts" / "windows" / "watchdog_tunnel.ps1",
]
FORBIDDEN_IP = "161.200.90.3"


def _read_caddyfile() -> str:
    if not CADDYFILE.exists():
        pytest.fail(
            f"{CADDYFILE} does not exist yet. This test is written test-first "
            "per T086 and is expected to fail until deploy/caddy/Caddyfile is created."
        )
    return CADDYFILE.read_text(encoding="utf-8")


def _directives_only(text: str) -> str:
    """Strip full-line comments (leading '#') so directive-focused checks
    aren't tripped up by explanatory prose that legitimately names things
    like "basic_auth" or an IP address for documentation purposes. Only
    used by checks about actual Caddy directives; the forbidden-IP scan
    intentionally does NOT use this - that check must catch a bare address
    anywhere in deploy/, comments included, per the project's hard
    constraint on 161.200.90.3."""
    return "\n".join(line for line in text.splitlines() if not line.strip().startswith("#"))


def test_no_basic_auth() -> None:
    text = _directives_only(_read_caddyfile())
    assert not re.search(r"\bbasic_?auth\b", text, re.IGNORECASE), (
        "Caddyfile must not configure a site-wide login (basic_auth) as an "
        "active directive. The owner-approved policy is per-job capability "
        "tokens only."
    )


def test_upstream_is_tunnel_address_only() -> None:
    raw = _read_caddyfile()
    directives = _directives_only(raw)
    # The upstream must be parameterized (never a hardcoded literal IP/host)
    # and must never point at 0.0.0.0, ::, or ComfyUI's port.
    assert "{$UPSTREAM_ORIGIN}" in raw, (
        "reverse_proxy upstream must use the {$UPSTREAM_ORIGIN} placeholder, "
        "not a hardcoded address."
    )
    for forbidden in ("0.0.0.0", "::", ":8188"):
        assert forbidden not in directives, f"Caddyfile must never reference {forbidden!r} as an upstream directive."


def test_no_hardcoded_hostname_or_ip_literal() -> None:
    raw = _read_caddyfile()
    directives = _directives_only(raw)
    assert "{$PUBLIC_HOSTNAME}" in raw, "The site block must use {$PUBLIC_HOSTNAME}, not a literal hostname."
    # No IPv4 literal should appear as an active directive (the catch-all
    # block legitimately uses bare :443/:80, which is fine - it has no host
    # part). Explanatory comments may still name the approved address for
    # documentation purposes.
    ipv4_literal = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")
    assert not ipv4_literal.search(directives), (
        "Caddyfile must not use any literal IPv4 address as an active directive, "
        "including the approved edge address - it must always be reached via "
        "{$PUBLIC_HOSTNAME} / DNS, never hardcoded in a directive."
    )


def test_request_body_max_size_within_policy() -> None:
    text = _read_caddyfile()
    match = re.search(r"max_size\s+(\d+)\s*(MB|MiB)", text, re.IGNORECASE)
    assert match, "Caddyfile must set request_body max_size."
    value = int(match.group(1))
    assert 10 <= value <= 16, (
        f"max_size is {value}{match.group(2)}; must stay in [10, 16] MiB. "
        "It must be looser than the API's 10 MiB policy (to avoid rejecting "
        "legal uploads due to multipart framing overhead) but still act as "
        "an absurdity guard, not a de facto unlimited size."
    )


def test_job_token_never_rewritten_or_stripped_from_request() -> None:
    text = _read_caddyfile()
    assert "X-Job-Token" not in re.sub(r"(?m)^\s*#.*$", "", text) or "delete" in text, (
        "If X-Job-Token is referenced outside of the log-redaction block, "
        "confirm manually it is not being altered on the request path."
    )
    # No header_up directive should touch X-Job-Token.
    assert not re.search(r"header_up\s+[-+]?X-Job-Token", text, re.IGNORECASE), (
        "Caddyfile must not add, remove, or rewrite the X-Job-Token request header."
    )


def test_job_token_deleted_from_access_log() -> None:
    text = _read_caddyfile()
    log_block_match = re.search(r"log\s*\{(.*?)\n\t\}", text, re.DOTALL)
    assert log_block_match, "Caddyfile must define a log block."
    log_block = log_block_match.group(1)
    assert "format filter" in log_block, "The log block must use `format filter` to redact sensitive headers."
    assert re.search(r"request>headers>X-Job-Token\s+delete", log_block), (
        "The log block must delete request>headers>X-Job-Token. Caddy's built-in "
        "redaction only covers Authorization/Cookie - X-Job-Token would otherwise "
        "be written to the access log in cleartext, violating the no-token-in-logs "
        "requirement (T091)."
    )


def test_admin_api_disabled() -> None:
    text = _read_caddyfile()
    assert re.search(r"(?m)^\s*admin\s+off\s*$", text), "Caddy's admin API must be disabled (`admin off`)."


def test_maintenance_page_on_upstream_failure() -> None:
    text = _read_caddyfile()
    assert "handle_errors" in text, (
        "Caddyfile must define handle_errors so an unreachable GPU laptop shows "
        "a maintenance page, not a raw 502."
    )
    assert re.search(r"\[?50[234]\]?", text), "handle_errors must match on upstream failure status codes (502/503/504)."


def test_forbidden_ip_absent_from_deployment_config() -> None:
    """161.200.90.3 must never appear in anything that configures or probes
    the network. It MAY appear in docs/ and evidence/ (which must be free to
    explain the restriction) and in this test file itself."""
    offenders: list[str] = []
    for target in FORBIDDEN_IP_SCAN_PATHS:
        if not target.exists():
            continue
        files = [target] if target.is_file() else [p for p in target.rglob("*") if p.is_file()]
        for path in files:
            if path.suffix in {".exe", ".log"}:
                continue
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if FORBIDDEN_IP in content:
                offenders.append(str(path.relative_to(REPO_ROOT)))
    assert not offenders, (
        f"{FORBIDDEN_IP} must never appear in deployment configuration or network "
        f"scripts. Found it in: {', '.join(offenders)}"
    )


def test_no_http_block_written_by_hand() -> None:
    text = _read_caddyfile()
    assert not re.search(r"(?m)^\s*http://", text), (
        "Do not hand-write an http:// block - Caddy's automatic HTTPS already "
        "redirects HTTP to HTTPS and serves the ACME HTTP-01 challenge; a "
        "hand-written block risks shadowing the challenge handler."
    )
