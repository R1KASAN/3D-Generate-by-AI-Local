from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8").lower()


def test_single_node_start_stop_have_the_approved_order_and_rollback():
    start = text("scripts/windows/start_single_node.ps1")
    stop = text("scripts/windows/stop_single_node.ps1")
    assert start.index("local3d-comfyui") < start.index("local3d-api") < start.index("local3d-web") < start.index("local3d-caddy")
    assert stop.index("local3d-caddy") < stop.index("local3d-web") < stop.index("local3d-api") < stop.index("local3d-comfyui")
    assert "rollback" in start
    assert "cloudflared" not in start + stop


def test_single_host_installer_is_application_only():
    installer = text("scripts/windows/install_single_host_entry.ps1")
    assert "install_winsw_services.ps1" in installer
    assert "local3d-tunnel" not in installer
    assert "cloudflared" not in installer
    assert "8443" not in installer and "20241" not in installer


def test_quick_tunnel_is_operator_run_and_loopback_only():
    launcher = text("scripts/windows/start_quick_tunnel.ps1")
    stopper = text("scripts/windows/stop_quick_tunnel.ps1")
    assert "'tunnel', '--url'" in launcher
    assert "127.0.0.1:${caddyport}" in launcher
    assert "'--loglevel', 'info'" in launcher
    assert "service install" not in launcher
    assert "tunnel --token" not in launcher and "service install" not in launcher
    assert "quick-tunnel.json" in launcher and "quick-tunnel.json" in stopper
    assert "stop-process" in stopper
    watchdog = text("scripts/windows/watchdog_tunnel.ps1")
    assert "diagnostic-only" in watchdog
    assert "restart-service" not in watchdog
    assert "start-process" not in watchdog


def test_service_verifier_covers_all_four_services_and_caddy_route():
    verifier = text("scripts/windows/verify_services.ps1")
    for name in ("local3d-comfyui", "local3d-api", "local3d-web", "local3d-caddy"):
        assert name in verifier
    for port in ("127.0.0.1:8188", "127.0.0.1:8000", "127.0.0.1:3000", "127.0.0.1:8080"):
        assert port in verifier
    assert "cloudflared" not in verifier
