import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/verify'))
from _streaming import streaming_check


def test_streaming_cannot_pass_without_complete_maximum_transfer_trace(tmp_path):
    assert streaming_check(None).verdict == 'BLOCKED'
    path = tmp_path / 'observation.json'
    path.write_text(json.dumps({'before': [], 'after': []}))
    assert streaming_check(path).verdict == 'BLOCKED'


def test_attested_trace_fails_on_even_transient_spool(tmp_path):
    path = tmp_path / 'observation.json'
    data = dict(operator_attested=True, approved_origin=True, trace_complete=True,
                maximum_download_tested=True, upload_bytes=10485760, download_bytes=20000000,
                project_spool_or_complete_body_files=1)
    path.write_text(json.dumps(data))
    assert streaming_check(path).verdict == 'FAIL'
    data['project_spool_or_complete_body_files'] = 0
    path.write_text(json.dumps(data))
    assert streaming_check(path).verdict == 'PASS'
