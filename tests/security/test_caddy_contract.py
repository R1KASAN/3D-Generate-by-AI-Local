"""Static contract for the single-node feature-004 Caddy edge."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CADDYFILE = ROOT / "deploy/caddy/Caddyfile"


def text() -> str:
    if not CADDYFILE.is_file():
        pytest.fail(f"missing {CADDYFILE}")
    return CADDYFILE.read_text(encoding="utf-8")


def active() -> str:
    return "\n".join(line for line in text().splitlines() if not line.strip().startswith("#"))


def test_single_loopback_listener_and_proxy_targets() -> None:
    body = active()
    assert re.search(r"(?m)^\s*:8080\s*\{", body)
    assert re.search(r"(?m)^\s*bind\s+127\.0\.0\.1\s*$", body)
    assert "{$API_UPSTREAM}" in body
    assert "{$WEB_UPSTREAM}" in body
    assert ":8188" not in body
    assert ":8443" not in body
    assert "UPSTREAM_ORIGIN" not in body


def test_path_split_is_explicit_and_preserves_api_prefix() -> None:
    body = active()
    assert re.search(r"@api\s+path\s+/api\s+/api/\*", body)
    assert body.count("reverse_proxy") == 2
    assert "handle_path" not in body


def test_loopback_and_no_public_tls_or_auth() -> None:
    body = active()
    assert "0.0.0.0" not in body and not re.search(r"(?m)^\s*:443\s*\{", body) and not re.search(r"(?m)^\s*:80\s*\{", body)
    assert "tls" not in body.lower()
    assert "basic_auth" not in body
    assert re.search(r"(?m)^\s*admin\s+off\s*$", body)


def test_size_cache_and_timeout_controls() -> None:
    body = active()
    assert re.search(r"request_body\s*\{[^}]*max_size\s+12MB", body, re.S)
    assert "Cache-Control \"no-store\"" in body
    assert "response_header_timeout 5s" in body
    assert "dial_timeout 2s" in body
    assert "buffer_requests" not in body and "buffer_responses" not in body


def test_sensitive_fields_are_removed_from_access_and_error_logs() -> None:
    body = text()
    assert "log default" in body
    for field in ("X-Job-Token", "Cookie", "Authorization"):
        assert re.search(rf"request>headers>{field}\s+delete", body)
    assert "request>headers delete" in body
    assert "request>uri delete" in body
    assert "request>remote_ip delete" in body


def test_maintenance_page_is_project_controlled() -> None:
    body = active()
    assert "handle_errors" in body
    assert re.search(r"root\s+\*\s+\{\$CADDY_MAINTENANCE_ROOT", body)
    assert (ROOT / "deploy/caddy/maintenance/maintenance.html").is_file()
