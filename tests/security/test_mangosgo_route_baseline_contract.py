from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts/verify" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_capture_allowlist_is_read_only_and_mango_scoped() -> None:
    module = load("capture_mangosgo_baseline")
    assert module.validate_target("https://www.mangosgo.com", ["/mango74", "/mango74/"]) == "https://www.mangosgo.com"
    with pytest.raises(ValueError):
        module.validate_target("https://evil.example", ["/mango74/"])
    with pytest.raises(ValueError):
        module.validate_target("https://www.mangosgo.com", ["/admin"])


def test_compare_flags_route_and_content_changes() -> None:
    module = load("compare_mangosgo_baseline")
    before = {"routes": [{"path": "/mango74/", "status": 200, "sha256": "a", "headers": {}}]}
    assert module.compare(before, before) == []
    after = {"routes": [{"path": "/mango74/", "status": 500, "sha256": "b", "headers": {}}]}
    assert module.compare(before, after)


def test_nt_nginx_snippet_owns_only_mango74() -> None:
    snippet = (ROOT / "deploy" / "nt-server" / "mango74-static.conf").read_text(
        encoding="utf-8"
    )
    assert "location = /mango74" in snippet
    assert "return 308 /mango74/;" in snippet
    assert "location ^~ /mango74/_next/" in snippet
    assert "location ^~ /mango74/" in snippet
    assert "try_files $uri $uri/ /mango74/index.html;" in snippet
    assert "location / {" not in snippet
    assert "proxy_pass" not in snippet


def test_nt_activation_script_is_scoped_and_recoverable() -> None:
    script = (ROOT / "deploy" / "nt-server" / "activate-mango74.sh").read_text(
        encoding="utf-8"
    )
    assert "/etc/nginx/sites-available/default" in script
    assert "www\\.mangosgo\\.com" in script
    assert "sudo nginx -t" in script
    assert "sudo systemctl reload nginx" in script
    assert "sudo systemctl stop" not in script
    assert "sudo cp -a \"$backup_config\" \"$config\"" in script
    assert "expected_snippet_hash" in script
    assert "expected_config_hash" in script
    assert "--noproxy '*'" in script
    assert "for attempt in $(seq 1 15)" in script
