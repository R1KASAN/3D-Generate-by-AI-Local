from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_recovery_runner_is_three_trial_and_reboot_safe() -> None:
    script = (ROOT / "scripts/windows/run_feature005_recovery_matrix.ps1").read_text(encoding="utf-8")
    assert "TrialCount = 3" in script
    assert "Full Notebook reboot is intentionally excluded" in script
    assert "Local3D-Nginx" in script
    assert "'cloudflared'" in script
    assert "required restart services are not installed" in script
    assert "127.0.0.1:8188/system_stats" in script
    assert "Before" in script and "After" in script


def test_deployment_recorder_rejects_sensitive_values() -> None:
    script = (ROOT / "scripts/verify/record_feature005_deployment.py").read_text(encoding="utf-8")
    assert "FORBIDDEN" in script
    assert "trycloudflare" in script
