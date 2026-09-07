"""Execute the feature-004 watchdog as a diagnostic-only helper."""

import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
PS = shutil.which("powershell") or shutil.which("pwsh")


@pytest.mark.skipif(not PS, reason="PowerShell required")
def test_watchdog_records_health_without_tunnel_or_service_mutation(tmp_path):
    script = tmp_path / "watchdog_tunnel.ps1"
    shutil.copyfile(ROOT / "scripts/windows/watchdog_tunnel.ps1", script)
    health = tmp_path / "health_chain.ps1"
    health.write_text("Write-Output '{\"Caddy\":{\"Healthy\":true}}'", encoding="utf-8")
    state = tmp_path / "state.json"
    result = subprocess.run(
        [PS, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script), "-HealthScript", str(health), "-StatePath", str(state)],
        env={**os.environ, "ProgramData": str(tmp_path)},
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    assert state.exists()
    assert json.loads(state.read_text(encoding="utf-8-sig"))["health"]
    assert "diagnostic-only" in result.stdout.lower()
