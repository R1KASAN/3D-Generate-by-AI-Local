from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "verify"))
from validate_contracts import validate_openapi, validate_manifest  # noqa: E402


def test_current_openapi_and_manifest_pass_contract_validation():
    openapi = ROOT / "specs/004-secure-ai-test-access/contracts/openapi.yaml"
    manifest = ROOT / "workflows/hunyuan3d/workflow-manifest.json"
    assert validate_openapi(openapi) == []
    assert validate_manifest(manifest) == []


def test_missing_openapi_is_fail_closed(tmp_path):
    errors = validate_openapi(tmp_path / "missing.yaml")
    assert errors and "cannot be parsed" in errors[0]
