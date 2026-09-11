from __future__ import annotations

from fastapi.testclient import TestClient

from local3d.config import Settings
from local3d.main import create_app


def _client(*, preview_enabled: bool = False) -> TestClient:
    settings = Settings(
        app_env="test",
        cors_preview_origin_enabled=preview_enabled,
    )
    return TestClient(create_app(settings))


def test_production_origin_receives_only_required_cors_headers() -> None:
    with _client() as client:
        response = client.options(
            "/api/v1/health/live",
            headers={
                "Origin": "https://www.mangosgo.com",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "X-Job-Token",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://www.mangosgo.com"
    assert "access-control-allow-credentials" not in response.headers
    assert "X-Job-Token" in response.headers["access-control-allow-headers"]
    assert response.headers["vary"] == "Origin"


def test_lookalike_http_and_null_origins_receive_no_allow_origin() -> None:
    for origin in (
        "http://www.mangosgo.com",
        "https://www.mangosgo.com.evil.example",
        "https://evil.example",
        "null",
    ):
        with _client() as client:
            response = client.options(
                "/api/v1/health/live",
                headers={
                    "Origin": origin,
                    "Access-Control-Request-Method": "GET",
                },
            )
        assert response.status_code == 400
        assert "access-control-allow-origin" not in response.headers


def test_firebase_origin_is_opt_in_and_independent() -> None:
    with _client(preview_enabled=False) as disabled_client:
        disabled = disabled_client.options(
            "/api/v1/health/live",
            headers={"Origin": "https://inw3d-ai-local.web.app", "Access-Control-Request-Method": "GET"},
        )
    assert disabled.status_code == 400

    with _client(preview_enabled=True) as enabled_client:
        enabled = enabled_client.options(
            "/api/v1/health/live",
            headers={"Origin": "https://inw3d-ai-local.web.app", "Access-Control-Request-Method": "GET"},
        )
    assert enabled.status_code == 200
    assert enabled.headers["access-control-allow-origin"] == "https://inw3d-ai-local.web.app"


def test_allowed_origin_without_job_token_is_still_unauthorized() -> None:
    with _client() as client:
        response = client.get(
            "/api/v1/jobs/00000000-0000-4000-8000-000000000001",
            headers={"Origin": "https://www.mangosgo.com"},
        )
    assert response.status_code == 404
    assert response.headers["access-control-allow-origin"] == "https://www.mangosgo.com"
    assert response.json()["error"]["code"] == "job_not_found"


def test_denied_origin_cannot_read_success_or_error_cors_body() -> None:
    with _client() as client:
        for path in ("/api/v1/health/live", "/api/v1/jobs/00000000-0000-4000-8000-000000000001"):
            response = client.get(path, headers={"Origin": "https://unapproved.example"})
            assert "access-control-allow-origin" not in response.headers
