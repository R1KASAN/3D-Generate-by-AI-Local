"""Validate operator metadata from an origin-local filesystem trace.

This is attested manual evidence, not independent observation by this verifier.
Never copy raw traces, paths, tokens, or transfer content into this record.
"""
import json
from pathlib import Path

from _evidence import Check


def streaming_check(path: Path | None) -> Check:
    expected = 'complete origin-local filesystem trace throughout maximum upload and download'
    if path is None:
        return Check('streaming-observation', 'operator trace metadata missing; snapshots cannot exclude transient files', expected, 'BLOCKED')
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        required = ('operator_attested', 'approved_origin', 'trace_complete', 'maximum_download_tested')
        if not isinstance(data, dict) or not all(data.get(key) is True for key in required):
            raise ValueError
        if data.get('upload_bytes') != 10 * 1024 * 1024:
            raise ValueError
        if type(data.get('download_bytes')) is not int or data['download_bytes'] <= 0:
            raise ValueError
        count = data.get('project_spool_or_complete_body_files')
        if type(count) is not int or count < 0:
            raise ValueError
    except (OSError, ValueError, TypeError):
        return Check('streaming-observation', 'missing or incomplete operator trace metadata', expected, 'BLOCKED')
    return Check('streaming-observation', f'operator-attested complete trace: {count} project-authored spool/body files', expected, 'PASS' if count == 0 else 'FAIL')
