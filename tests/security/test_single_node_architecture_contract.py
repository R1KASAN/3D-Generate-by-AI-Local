"""Feature-004 architecture guardrails for active deployment files."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _active_files() -> list[Path]:
    paths = [ROOT / "deploy/caddy/Caddyfile", ROOT / "deploy/caddy/.env.example", ROOT / "deploy/cloudflared/quick-tunnel.md", ROOT / "scripts/windows/install_winsw_services.ps1"]
    paths.extend((ROOT / "deploy/windows/services").glob("*.xml"))
    return [path for path in paths if path.is_file()]


def test_active_deployment_has_one_loopback_server_and_no_edge_origin() -> None:
    content = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in _active_files())
    assert "161.200.90.4" not in content
    assert "UPSTREAM_ORIGIN" not in content
    assert "10.10.0.2" not in content
    assert "WireGuard" not in content
    assert "cloudflared tunnel --url http://127.0.0.1:8080" in content
    assert "127.0.0.1:3000" in content
    assert "127.0.0.1:8000" in content
    assert "127.0.0.1:8188" in content


def test_no_direct_internet_bindings_are_declared() -> None:
    content = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in _active_files())
    assert "0.0.0.0" not in content
    assert "PUBLIC_HOSTNAME" not in content
    assert "credentials-file" not in content
