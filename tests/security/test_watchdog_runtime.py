"""Execute the watchdog with fake health/service functions in an isolated folder."""
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
PS = shutil.which('powershell') or shutil.which('pwsh')


def run_fake(tmp_path, *, binding=True, engine=True):
    script = tmp_path / 'watchdog_tunnel.ps1'
    shutil.copyfile(ROOT / 'scripts/windows/watchdog_tunnel.ps1', script)
    (tmp_path / 'health_chain.ps1').write_text('''
function Test-PrivateBindingHealth { return @{ Healthy = ($env:TEST_BINDING -eq 'true'); Detail = 'fake' } }
function Test-JobServiceHealth { return @{ Healthy = $true; Detail = 'fake' } }
function Test-GpuHealth { return @{ Healthy = $true; Detail = 'fake' } }
function Test-AiEngineHealth { return @{ Healthy = ($env:TEST_ENGINE -eq 'true'); Detail = 'fake' } }
function Restart-Service { param($Name, [switch]$Force, $ErrorAction) Add-Content -LiteralPath $env:TEST_CALLS -Value $Name; throw 'synthetic restart failure' }
''', encoding='utf-8')
    result = subprocess.run([PS, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(script), '-StateFile', str(tmp_path / 'state.json'), '-CooldownMinutes', '0'], env={**os.environ, 'ProgramData': str(tmp_path), 'TEST_CALLS': str(tmp_path / 'calls.txt'), 'TEST_BINDING': str(binding).lower(), 'TEST_ENGINE': str(engine).lower()}, capture_output=True, text=True, timeout=20)
    assert (tmp_path / 'state.json').exists(), result.stderr
    return result


@pytest.mark.skipif(not PS, reason='PowerShell required')
def test_failed_restart_attempts_stop_at_three(tmp_path):
    for _ in range(4):
        run_fake(tmp_path, binding=False)
    calls = (tmp_path / 'calls.txt').read_text().splitlines()
    assert len(calls) == 3


@pytest.mark.skipif(not PS, reason='PowerShell required')
def test_gpu_recovery_starts_grace_before_engine_restart(tmp_path):
    run_fake(tmp_path)
    state_path = tmp_path / 'state.json'
    state = json.loads(state_path.read_text(encoding='utf-8-sig'))
    state['GpuLastUnhealthyAt'] = '2020-01-01T00:00:00Z'
    state_path.write_text(json.dumps(state), encoding='utf-8')
    run_fake(tmp_path, engine=False)
    assert not (tmp_path / 'calls.txt').exists()
