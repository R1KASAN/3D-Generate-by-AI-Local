"""Loopback-only proxy trials; never contact the approved origin or provider."""
import http.client
import json
import os
from pathlib import Path
import socket
import subprocess
import threading
import time
from urllib.parse import urlsplit
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest


ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.skipif(not os.environ.get("CADDY_BINARY"), reason="CADDY_BINARY required for real local proxy trial")
def test_proxy_correlation_cache_and_unavailable_without_secret_logs(tmp_path):
    state = {"engine": True, "request_id": None}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            health = urlsplit(self.path).path == '/api/v1/health/engine'
            status = 503 if health and not state['engine'] else 200
            if not health:
                state['request_id'] = self.headers.get('X-Request-ID')
            self.send_response(status)
            self.end_headers()
            self.wfile.write(b'upstream-content')

        def log_message(self, *args):
            pass

    upstream = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=upstream.serve_forever, daemon=True)
    thread.start()
    with socket.socket() as reservation:
        reservation.bind(('127.0.0.1', 0))
        port = reservation.getsockname()[1]
    access = tmp_path / 'access.log'
    runtime = tmp_path / 'runtime.log'
    config = tmp_path / 'Caddyfile'
    text = (ROOT / 'deploy/caddy/Caddyfile').read_text(encoding='utf-8')
    text = text.replace('127.0.0.1:8443', f'127.0.0.1:{port}')
    text = text.replace('/srv/caddy/maintenance', (ROOT / 'deploy/caddy/maintenance').as_posix())
    config.write_text(text, encoding='utf-8')
    env = {**os.environ, 'UPSTREAM_ORIGIN': f'http://127.0.0.1:{upstream.server_port}', 'CADDY_LOG_PATH': str(access)}
    secret = 'synthetic-must-never-be-logged'

    def request():
        connection = http.client.HTTPConnection('127.0.0.1', port, timeout=6)
        connection.request('GET', '/?token=' + secret, headers={'X-Job-Token': secret, 'X-Request-ID': secret})
        response = connection.getresponse()
        body = response.read()
        headers = dict(response.getheaders())
        connection.close()
        return response.status, headers, body

    with runtime.open('wb') as output:
        process = subprocess.Popen([os.environ['CADDY_BINARY'], 'run', '--config', str(config), '--adapter', 'caddyfile'], env=env, stdout=output, stderr=output, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        try:
            for _ in range(100):
                try:
                    status, headers, body = request()
                    break
                except ConnectionRefusedError:
                    time.sleep(.05)
            else:
                pytest.fail('local Caddy did not start')
            assert status == 200
            request_id = headers['X-Request-Id']
            assert request_id != secret and request_id == state['request_id']
            assert headers['Cache-Control'] == 'no-store'
            state['engine'] = False
            started = time.monotonic()
            status, headers, body = request()
            assert status == 503
            assert time.monotonic() - started < 5
            assert headers['Cache-Control'] == 'no-store'
            assert b'upstream-content' not in body
            upstream.shutdown()
            upstream.server_close()
            started = time.monotonic()
            status, headers, body = request()
            assert status in (502, 503, 504)
            assert time.monotonic() - started < 5
            assert headers['Cache-Control'] == 'no-store'
        finally:
            process.terminate()
            process.wait(timeout=10)
            upstream.shutdown()
            upstream.server_close()
    logs = access.read_text(encoding='utf-8') + runtime.read_text(encoding='utf-8')
    assert secret not in logs
    entries = [json.loads(line) for line in access.read_text(encoding='utf-8').splitlines()]
    assert any(e.get('request_id') == request_id for e in entries)
