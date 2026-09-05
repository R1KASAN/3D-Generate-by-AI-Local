"""Static contract tests for deploy/caddy/Caddyfile (feature 003).

Feature 003 replaces feature 002's inbound origin proxy (public :443
listener, Origin CA certificate, Authenticated Origin Pulls / mTLS) with an
outbound Cloudflare Tunnel connector. Caddy's role shrinks to a stateless,
loopback-only streaming pass-through between the connector and the GPU
laptop - see specs/003-outbound-tunnel-entry/contracts/origin-entry.md.

These tests never start Caddy or touch the network - they parse the
Caddyfile text and assert:

  - no public listener of any kind (no :443/:80 site block, no TLS/mTLS
    config, no Origin CA or client-CA file references) - cloudflared alone
    owns the provider-facing hop now
  - the listener is loopback-only
  - no site-wide login (basic_auth) - the requested policy is per-job
    capability tokens only
  - the only upstream is the WireGuard tunnel address to the GPU laptop,
    never 0.0.0.0/::, never ComfyUI's port (:8188) directly
  - request and response bodies are streamed, never buffered to disk
    (FR-014a) - buffer_requests/buffer_responses must be absent
  - X-Job-Token/Cookie/Authorization are stripped from the access log
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
# why .3 is off-limits.
FORBIDDEN_IP_SCAN_PATHS = [
    REPO_ROOT / "deploy",
    REPO_ROOT / "scripts" / "windows" / "start_web_service.ps1",
    REPO_ROOT / "scripts" / "windows" / "watchdog_tunnel.ps1",
]
FORBIDDEN_IP = "161.200.90.3"


def _read_caddyfile() -> str:
    if not CADDYFILE.exists():
        pytest.fail(f"{CADDYFILE} does not exist.")
    return CADDYFILE.read_text(encoding="utf-8")


def _directives_only(text: str) -> str:
    """Strip full-line comments (leading '#') so directive-focused checks
    aren't tripped up by explanatory prose. Only used by checks about actual
    Caddy directives; the forbidden-IP scan intentionally does NOT use this."""
    return "\n".join(line for line in text.splitlines() if not line.strip().startswith("#"))


def test_no_basic_auth() -> None:
    text = _directives_only(_read_caddyfile())
    assert not re.search(r"\bbasic_?auth\b", text, re.IGNORECASE), (
        "Caddyfile must not configure a site-wide login (basic_auth) as an "
        "active directive. The requested policy is per-job capability "
        "tokens only."
    )


def test_no_public_listener() -> None:
    """FR-003/FR-004: the origin has no inbound public port at all. Only
    cloudflared dials out; Caddy never listens on :443 or :80."""
    text = _directives_only(_read_caddyfile())
    assert not re.search(r"(?m)^\s*:443\b", text), "The origin must not listen on :443 - there is no inbound port."
    assert not re.search(r"(?m)^\s*:80\b", text), "The origin must not listen on :80."
    assert "{$PUBLIC_HOSTNAME}" not in text, (
        "The Caddyfile must not key a site block on the public hostname - "
        "that hostname is resolved by the provider edge, not by this loopback proxy."
    )


def test_no_tls_or_client_certificate_config() -> None:
    """There is no provider-to-origin TLS hop for this process to
    authenticate anymore: cloudflared's outbound connection owns that.
    Feature 002's Origin CA + Authenticated Origin Pulls (mTLS) are removed,
    not reconfigured."""
    text = _directives_only(_read_caddyfile())
    assert not re.search(r"(?m)^\s*tls\b", text, re.IGNORECASE), "Caddy must not configure a tls block."
    assert "client_auth" not in text, "Caddy must not require a client certificate; there is no inbound TLS hop."
    assert "require_and_verify" not in text
    assert "trusted_ca_cert_file" not in text
    for forbidden in ("ORIGIN_CERT_PATH", "ORIGIN_KEY_PATH", "ORIGIN_PULL_CA_PATH"):
        assert forbidden not in text, f"{forbidden} is a feature-002 artifact and must not appear."
    assert not re.search(r"(?m)^\s*acme(?:\s|$)", text, re.IGNORECASE)
    assert not re.search(r"(?m)^\s*email\s+", text)


def test_listener_is_loopback_only() -> None:
    """FR-004: the pass-through must not be reachable from any interface
    other than loopback - cloudflared is the only process that reaches it."""
    text = _directives_only(_read_caddyfile())
    assert re.search(r"127\.0\.0\.1", text), "Caddyfile must bind an explicit loopback address."
    assert "0.0.0.0" not in text
    assert not re.search(r"(?<!127\.0\.0\.)1\b::(?!\w)", text)


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


def test_no_hardcoded_approved_address_literal() -> None:
    raw = _read_caddyfile()
    directives = _directives_only(raw)
    ipv4_literal = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")
    for match in ipv4_literal.finditer(directives):
        assert match.group(0).startswith("127.0.0."), (
            f"Unexpected IPv4 literal {match.group(0)!r} as an active directive; "
            "only the loopback listen address may be a literal."
        )


def test_streaming_pass_through_no_buffering() -> None:
    """FR-014a: request and response bodies must be streamed. Caddy's
    reverse_proxy streams by default; buffer_requests/buffer_responses
    would defeat that and must never be added."""
    text = _directives_only(_read_caddyfile())
    assert "buffer_requests" not in text, (
        "buffer_requests would spool the full request body to memory/disk "
        "before forwarding it, violating the streaming pass-through requirement."
    )
    assert "buffer_responses" not in text, (
        "buffer_responses would spool the full response (including generated "
        "artifacts) before returning it, adding latency and a temp-file "
        "footprint the origin must not have."
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
        "an absurdity guard, not a de facto unlimited size. This limit MUST "
        "be enforced during the stream, not after buffering the full body."
    )


def test_job_token_never_rewritten_or_stripped_from_request() -> None:
    text = _read_caddyfile()
    assert "X-Job-Token" not in re.sub(r"(?m)^\s*#.*$", "", text) or "delete" in text, (
        "If X-Job-Token is referenced outside of the log-redaction block, "
        "confirm manually it is not being altered on the request path."
    )
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
        "requirement (FR-017)."
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


def test_origin_correlation_and_all_response_cache_policy():
    text = _directives_only(_read_caddyfile())
    assert 'log_append <request_id {http.request.uuid}' in text
    assert 'header_up X-Request-ID {http.request.uuid}' in text
    assert 'request>uri delete' in text
    assert 'request>headers delete' in text
    assert 'request>remote_ip delete' in text
    assert 'request>client_ip delete' in text
    assert 'Strict-Transport-Security' in text
    assert 'Cache-Control "no-store"' in text.split('reverse_proxy')[0]


def test_proxy_matches_connector_and_quickstart_port():
    text = _directives_only(_read_caddyfile())
    config = (REPO_ROOT / 'deploy/cloudflared/config.yml.example').read_text(encoding='utf-8')
    quickstart = (REPO_ROOT / 'specs/003-outbound-tunnel-entry/quickstart.md').read_text(encoding='utf-8')
    endpoint = re.search(r'http://127\.0\.0\.1:\d+', text).group()
    assert endpoint in config
    assert f'--url {endpoint}' in quickstart
