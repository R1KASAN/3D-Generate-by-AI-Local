from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "verify"))
from test_log_redaction import scan  # noqa: E402


def test_clean_fixture_tree_has_no_secret_findings(tmp_path):
    (tmp_path / "safe.md").write_text("temporary non-production test service\n", encoding="utf-8")
    assert scan(tmp_path, []) == []


def test_scanner_reports_rule_without_echoing_value(tmp_path):
    (tmp_path / "bad.md").write_text("sentinel-value", encoding="utf-8")
    findings = scan(tmp_path, ["sentinel-value"])
    assert findings == [("bad.md", "supplied-sentinel")]
