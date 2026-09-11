from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_nginx_service_definition_is_loopback_proxy_only() -> None:
    definition = (ROOT / "deploy/windows/services/nginx.xml").read_text(encoding="utf-8")
    assert "<id>Local3D-Nginx</id>" in definition
    assert "nginx.exe" in definition
    assert 'C:\\ProgramData\\Local3D\\nginx\\nginx.conf' in definition
    assert '..\\..\\..' not in definition
    assert "127.0.0.1" not in definition or "8080" in definition
    assert "daemon off" in definition
    assert "<depend>Local3D-API</depend>" in definition


def test_old_caddy_definition_is_kept_for_explicit_rollback() -> None:
    assert (ROOT / "deploy/windows/services/caddy.xml").exists()


def test_feature005_installer_has_reversible_nginx_cutover() -> None:
    script = (ROOT / "scripts/windows/install_winsw_services.ps1").read_text(encoding="utf-8")
    assert "[switch]$Feature005" in script
    assert "Local3D-Nginx" in script
    assert "Set-Service -Name 'Local3D-Caddy' -StartupType Disabled" in script
    assert "ExpectedNginxSha256" in script
    assert "-t -p" in script
    assert script.index("Stop-Service -Name 'Local3D-Caddy' -Force") < script.index("& $nginxSource -t")
    assert "temp\\client_body_temp" in script
    assert "nginxServiceRoot" in script
    assert "OrdinalIgnoreCase.Equals" in script
    assert "nginxDestination" in script


def test_feature005_operator_scripts_are_bounded_and_loopback_only() -> None:
    start = (ROOT / "scripts/windows/start_nginx_service.ps1").read_text(encoding="utf-8")
    stop = (ROOT / "scripts/windows/stop_nginx_service.ps1").read_text(encoding="utf-8")
    recovery = (ROOT / "scripts/windows/run_feature005_recovery_matrix.ps1").read_text(encoding="utf-8")
    assert "Local3D-Caddy" in start and "non-loopback" in start
    assert "Local3D-Nginx" in start and "8080" in stop
    assert "ExecuteReboot" in recovery and "intentionally excluded" in recovery


def test_feature005_runbooks_define_independent_rollbacks() -> None:
    production = (ROOT / "docs/runbooks/mango74-production.md").read_text(encoding="utf-8")
    rollback = (ROOT / "docs/runbooks/mango74-rollback.md").read_text(encoding="utf-8")
    assert "named Tunnel" in production and "NT Server" in production
    assert "Frontend only" in rollback and "Nginx/proxy" in rollback and "Tunnel/API" in rollback
