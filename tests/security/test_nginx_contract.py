from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_nginx_is_loopback_only_and_proxies_only_to_fastapi() -> None:
    config = (ROOT / "../deploy/nginx/nginx.conf").resolve().read_text(encoding="utf-8")
    assert "listen 127.0.0.1:8080" in config
    assert "listen 0.0.0.0" not in config
    assert "proxy_pass http://127.0.0.1:8000" in config
    assert "127.0.0.1:8188" not in config
    assert "mango74-api.mangosgo.com" in config
    assert "client_max_body_size 10m" in config
    # The NT Server reaches this origin only over the private WireGuard tunnel
    # address (deploy/wireguard/), never a routable interface.
    assert "listen 10.10.0.2:8080" in config
    assert "www.mangosgo.com" in config


def test_nginx_error_page_contains_no_internal_details() -> None:
    page = (ROOT / "../deploy/nginx/errors/50x.html").resolve().read_text(encoding="utf-8")
    assert "127.0.0.1" not in page
    assert "stack" not in page.lower()
    assert "Service unavailable" in page
