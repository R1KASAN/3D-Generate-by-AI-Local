from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_failure_matrix_contract_names_all_required_cases_and_safe_evidence() -> None:
    script = (ROOT / "scripts/windows/run_operations_matrix.ps1").read_text(encoding="utf-8")
    assert "[switch]$Feature005" in script
    assert "invalid-upload-and-capacity" in script
    assert "restart-and-dependency-recovery" in script
    for case in ("caddy-failure-diagnosis", "web-failure-diagnosis", "api-failure-diagnosis", "engine-failure-diagnosis", "clean-restart"):
        assert case in script
    assert "EvidencePath" in script and "Quick Tunnel" in script


def test_feature005_failure_evidence_directory_exists() -> None:
    assert (ROOT / "evidence/feature-005").is_dir()
