"""Real local Caddy trial using only ephemeral loopback mock upstreams."""

from __future__ import annotations

import http.client
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import socket
import subprocess
import threading
import time

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.skipif(not os.environ.get("CADDY_BINARY"), reason="CADDY_BINARY required")
def test_caddy_routes_api_and_web_and_returns_maintenance(tmp_path: Path) -> None:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            body = b"api" if self.path.startswith("/api") else b"web"
            self.send_response(200)
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args: object) -> None:
            return

    web = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    api = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    for server in (web, api):
        threading.Thread(target=server.serve_forever, daemon=True).start()
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    config = tmp_path / "Caddyfile"
    config.write_text(
        (ROOT / "deploy/caddy/Caddyfile").read_text(encoding="utf-8"), encoding="utf-8"
    )
    log = tmp_path / "caddy.log"
    env = {
        **os.environ,
        "CADDY_BINARY": os.environ["CADDY_BINARY"],
        "WEB_UPSTREAM": f"http://127.0.0.1:{web.server_port}",
        "API_UPSTREAM": f"http://127.0.0.1:{api.server_port}",
        "CADDY_LOG_PATH": str(log),
        "CADDY_MAINTENANCE_ROOT": str(ROOT / "deploy/caddy/maintenance"),
    }
    # Keep the contract listener loopback-only while avoiding a collision.
    config.write_text(config.read_text(encoding="utf-8").replace(":8080", f":{port}"), encoding="utf-8")
    process = subprocess.Popen(
        [env["CADDY_BINARY"], "run", "--config", str(config), "--adapter", "caddyfile"],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )

    def get(path: str) -> tuple[int, bytes]:
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        connection.request("GET", path)
        response = connection.getresponse()
        result = response.status, response.read()
        connection.close()
        return result

    try:
        for _ in range(100):
            try:
                assert get("/") == (200, b"web")
                break
            except (ConnectionRefusedError, AssertionError):
                time.sleep(0.05)
        else:
            pytest.fail("Caddy did not start")
        assert get("/api/v1/health") == (200, b"api")
        web.shutdown()
        web.server_close()
        status, _ = get("/")
        assert status in (502, 503, 504)
    finally:
        process.terminate()
        process.wait(timeout=10)
        api.shutdown()
        api.server_close()
