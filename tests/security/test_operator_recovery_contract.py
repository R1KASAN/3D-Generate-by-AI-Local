from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read(name: str) -> str:
    return (ROOT / "scripts/windows" / name).read_text(encoding="utf-8").lower()


def test_recovery_runner_is_explicit_and_sanitized():
    runner = read("run_recovery_matrix.ps1")
    probe = read("check_reboot_probe.py")
    reboot = read("verify_reboot_recovery.ps1")
    assert "evidence\\feature-004\\us4-recovery-matrix.md" in runner
    assert "local3d-caddy" in runner
    assert "executeservicerestarts" in runner
    assert "queue_running" in runner and "queue_pending" in runner
    assert "orphan" in runner
    assert "job_id" in probe and "select status, error_code, attempt_count" in probe
    assert "engine_job_id" not in probe
    assert "trialcount" in reboot and "trialnumber" in reboot
    assert "probemode" in reboot and "queued" in reboot and "running" in reboot
    assert "300" in reboot and "local3d-caddy" in reboot
    assert "executereboot" in reboot and "afterreboot" in reboot
    assert "shutdown.exe /r" in reboot
    assert "job_token" not in reboot
