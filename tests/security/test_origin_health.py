import io
import sys
from pathlib import Path
import urllib.error

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/verify'))
from origin_health import probe


def test_edge_is_reachable_even_when_connector_is_down(monkeypatch):
    def unavailable(*args, **kwargs):
        raise urllib.error.HTTPError('https://example.org', 503, 'unavailable', {}, io.BytesIO())
    monkeypatch.setattr('urllib.request.urlopen', unavailable)
    assert probe('https://example.org', edge=True) == 'healthy'
    assert probe('http://127.0.0.1:20241/ready', edge=False) == 'failed'


def test_unobservable_health_is_unknown(monkeypatch):
    def unavailable(*args, **kwargs):
        raise urllib.error.URLError('offline')
    monkeypatch.setattr('urllib.request.urlopen', unavailable)
    assert probe('https://example.org', edge=True) == 'unknown'
