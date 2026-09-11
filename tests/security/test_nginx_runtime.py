"""Optional real Nginx loopback trial using ephemeral upstreams.

The suite is intentionally skipped unless ``NGINX_BINARY`` is supplied by an
operator. Static contract tests remain runnable on every development machine.
"""

from __future__ import annotations

import http.client
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import subprocess
import threading
import time
import socket

import pytest


def stop_nginx_process_tree(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is None:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


@pytest.mark.skipif(not os.environ.get("NGINX_BINARY"), reason="NGINX_BINARY required")
def test_nginx_routes_api_body_and_rejects_wrong_host(tmp_path: Path) -> None:
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            body = self.rfile.read(int(self.headers.get("content-length", "0")))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"path":"' + self.path.encode() + b'","body":"' + body + b'"}')

        def do_GET(self) -> None:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"live")

        def log_message(self, *_args: object) -> None:
            return

    upstream = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=upstream.serve_forever, daemon=True).start()
    (tmp_path / "logs").mkdir()
    for directory in ("client_body_temp", "proxy_temp", "fastcgi_temp", "uwsgi_temp", "scgi_temp"):
        (tmp_path / "temp" / directory).mkdir(parents=True)
    (tmp_path / "mime.types").write_text("types {}", encoding="utf-8")
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    config = tmp_path / "nginx.conf"
    config.write_text(
        f"""worker_processes 1;
events {{ worker_connections 32; }}
    http {{
      server_names_hash_bucket_size 64;
      include mime.types;
      server {{
        listen 127.0.0.1:{port} default_server;
        server_name _;
        return 404;
      }}
      server {{
        listen 127.0.0.1:{port};
        server_name mango74-api.mangosgo.com;
        client_max_body_size 1m;
        location /api/ {{ proxy_pass http://127.0.0.1:{upstream.server_port}; }}
        location / {{ return 404; }}
      }}
}}
""",
        encoding="utf-8",
    )
    process = subprocess.Popen(
        [os.environ["NGINX_BINARY"], "-p", str(tmp_path), "-c", str(config), "-g", "daemon off;"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )

    def request(method: str, path: str, *, host: str, body: bytes = b"") -> tuple[int, bytes]:
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        connection.request(method, path, body=body, headers={"Host": host, "Content-Length": str(len(body))})
        response = connection.getresponse()
        result = response.status, response.read()
        connection.close()
        return result

    try:
        for _ in range(100):
            try:
                if request("GET", "/", host="mango74-api.mangosgo.com")[0] in {404, 200}:
                    break
            except (ConnectionRefusedError, ConnectionResetError, http.client.HTTPException, OSError):
                time.sleep(0.05)
        assert request("GET", "/api/v1/health/live", host="mango74-api.mangosgo.com") == (200, b"live")
        status, body = request("POST", "/api/v1/jobs", host="mango74-api.mangosgo.com", body=b"payload")
        assert status == 200 and b"payload" in body
        assert request("GET", "/", host="mango74-api.mangosgo.com")[0] == 404
        assert request("GET", "/api/v1/health/live", host="unexpected.example")[0] == 404
    finally:
        stop_nginx_process_tree(process)
        upstream.shutdown()
        upstream.server_close()


@pytest.mark.skipif(not os.environ.get("NGINX_BINARY"), reason="NGINX_BINARY required")
def test_nginx_runtime_bounds_failures_and_malformed_hosts(tmp_path: Path) -> None:
    class SlowHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            time.sleep(2)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"late")

        def log_message(self, *_args: object) -> None:
            return

    slow = ThreadingHTTPServer(("127.0.0.1", 0), SlowHandler)
    threading.Thread(target=slow.serve_forever, daemon=True).start()
    refusal_probe = ThreadingHTTPServer(("127.0.0.1", 0), BaseHTTPRequestHandler)
    refusal_port = refusal_probe.server_port
    refusal_probe.server_close()

    (tmp_path / "logs").mkdir()
    (tmp_path / "temp" / "client_body_temp").mkdir(parents=True)
    (tmp_path / "temp" / "proxy_temp").mkdir(parents=True)
    (tmp_path / "mime.types").write_text("types {}\n", encoding="utf-8")
    (tmp_path / "errors").mkdir()
    (tmp_path / "errors" / "50x.html").write_text(
        "<!doctype html><title>Temporarily unavailable</title>", encoding="utf-8"
    )
    port_probe = ThreadingHTTPServer(("127.0.0.1", 0), BaseHTTPRequestHandler)
    port = port_probe.server_port
    port_probe.server_close()
    config = tmp_path / "nginx.conf"
    config.write_text(
        f"""worker_processes 1;
error_log logs/error.log warn;
pid logs/nginx.pid;
events {{ worker_connections 32; }}
http {{
  server_names_hash_bucket_size 64;
  include mime.types;
  client_max_body_size 1k;
  proxy_read_timeout 200ms;
  proxy_connect_timeout 200ms;
  error_page 400 404 413 500 502 503 504 /errors/50x.html;
  server {{
    listen 127.0.0.1:{port} default_server;
    server_name _;
    return 404;
  }}
  server {{
    listen 127.0.0.1:{port};
    server_name mango74-api.mangosgo.com;
    location /api/ {{ proxy_pass http://127.0.0.1:{refusal_port}; }}
    location /timeout/ {{ proxy_pass http://127.0.0.1:{slow.server_port}; }}
    location = /errors/50x.html {{ alias errors/50x.html; internal; }}
    location / {{ return 404; }}
  }}
}}
""",
        encoding="utf-8",
    )
    process = subprocess.Popen(
        [os.environ["NGINX_BINARY"], "-p", str(tmp_path), "-c", str(config), "-g", "daemon off;"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )

    def request(method: str, path: str, *, host: str, body: bytes = b"") -> tuple[int, bytes]:
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        connection.request(method, path, body=body, headers={"Host": host, "Content-Length": str(len(body))})
        response = connection.getresponse()
        result = response.status, response.read()
        connection.close()
        return result

    try:
        for _ in range(100):
            try:
                request("GET", "/", host="mango74-api.mangosgo.com")
                break
            except ConnectionRefusedError:
                time.sleep(0.05)
        refusal_status, refusal_body = request("GET", "/api/v1/health/live", host="mango74-api.mangosgo.com")
        assert refusal_status in {502, 504}
        assert b"127.0.0.1" not in refusal_body and str(tmp_path).encode() not in refusal_body

        timeout_status, timeout_body = request("GET", "/timeout/health", host="mango74-api.mangosgo.com")
        assert timeout_status == 504
        assert b"127.0.0.1" not in timeout_body and str(tmp_path).encode() not in timeout_body

        oversized_status, oversized_body = request(
            "POST", "/api/v1/jobs", host="mango74-api.mangosgo.com", body=b"x" * 2048
        )
        assert oversized_status == 413
        assert b"127.0.0.1" not in oversized_body and str(tmp_path).encode() not in oversized_body

        malformed_status, malformed_body = request("GET", "/api/v1/health/live", host="unexpected.example")
        assert malformed_status == 404
        assert b"127.0.0.1" not in malformed_body and str(tmp_path).encode() not in malformed_body
    finally:
        stop_nginx_process_tree(process)
        slow.shutdown()
        slow.server_close()
