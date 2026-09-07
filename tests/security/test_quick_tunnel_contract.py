from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_quick_tunnel_docs_and_launcher_are_runtime_only() -> None:
    docs = (ROOT / "deploy/cloudflared/quick-tunnel.md").read_text(encoding="utf-8")
    launcher = (ROOT / "scripts/windows/start_quick_tunnel.ps1").read_text(encoding="utf-8")
    for body in (docs, launcher):
        if body is docs:
            assert "cloudflared tunnel --url http://127.0.0.1:8080 --loglevel info" in body
        else:
            assert "tunnel --url" in body and "--loglevel info" in body
        assert "trycloudflare.com" in body
        assert "temporary" in body.lower()
        if body is docs:
            assert "credentials-file" not in body
        assert "tunnel create" not in body
        assert "cloudflared service install" not in body
    assert "config.yml" in launcher and "config.yaml" in launcher
    assert "CADDY_LOG_PATH" not in launcher


def test_quick_tunnel_launcher_rejects_named_config_and_does_not_write_url() -> None:
    launcher = (ROOT / "scripts/windows/start_quick_tunnel.ps1").read_text(encoding="utf-8")
    assert "throw" in launcher
    assert "Get-Content" in launcher
    assert "Set-Content" not in launcher
    assert "Out-File" not in launcher


def test_quick_tunnel_launcher_identifies_only_the_current_url_without_repeating_logs() -> None:
    launcher = (ROOT / "scripts/windows/start_quick_tunnel.ps1").read_text(encoding="utf-8")
    assert "TEMPORARY NON-PRODUCTION URL" in launcher
    assert "Error 1033" in launcher
    assert "Select-Object -Skip" in launcher
    assert "Remove-Item -LiteralPath $stdoutPath, $stderrPath" in launcher
    assert "A Quick Tunnel is already running" in launcher


def test_quick_tunnel_stopper_supports_explicit_elevation_and_pid_validation() -> None:
    stopper = (ROOT / "scripts/windows/stop_quick_tunnel.ps1").read_text(encoding="utf-8")
    assert "[switch]$Elevate" in stopper
    assert "-Verb RunAs" in stopper
    assert "Access is denied" in stopper
    assert "ProcessName -ne 'cloudflared'" in stopper
