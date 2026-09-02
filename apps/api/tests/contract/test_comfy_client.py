from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from local3d.adapters.generation.base import JobObservationStatus
from local3d.adapters.generation.comfy_client import ComfyClient


def _client(handler: httpx.AsyncBaseTransport) -> ComfyClient:
    transport = handler
    http = httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8188")
    return ComfyClient("http://127.0.0.1:8188", http_client=http)


@pytest.mark.asyncio
async def test_submit_queue_history_and_reconcile_keep_prompt_id_private() -> None:
    requests: list[tuple[str, str]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append((request.method, request.url.path))
        if request.method == "POST" and request.url.path == "/prompt":
            payload = json.loads(request.content)
            assert payload["prompt"] == {"1": {"class_type": "LoadImage"}}
            assert isinstance(payload["client_id"], str)
            return httpx.Response(200, json={"prompt_id": "engine-secret-123"})
        if request.method == "GET" and request.url.path == "/queue":
            return httpx.Response(
                200,
                json={
                    "queue_running": [],
                    "queue_pending": [[2, "engine-secret-123", {}, {}, "client"]],
                },
            )
        if request.method == "GET" and request.url.path == "/history/engine-secret-123":
            return httpx.Response(
                200,
                json={
                    "engine-secret-123": {
                        "status": {"status_str": "success", "completed": True},
                        "outputs": {"9": {"gltf": [{"filename": "model.glb"}]}},
                    }
                },
            )
        raise AssertionError(f"unexpected request {request.method} {request.url}")

    client = _client(httpx.MockTransport(handler))
    try:
        handle = await client.submit({"1": {"class_type": "LoadImage"}})
        assert handle.public_id is None
        assert "engine-secret-123" not in repr(handle)

        queue = await client.queue()
        assert queue.pending == 1
        assert queue.running == 0

        observation = await client.reconcile(handle)
        assert observation.status is JobObservationStatus.SUCCEEDED
        assert observation.candidates == (Path("model.glb"),)
        assert all("prompt_id" not in path for _, path in requests if path != "/history/engine-secret-123")
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_queue_maps_running_and_pending_engine_entries() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/queue"
        return httpx.Response(
            200,
            json={
                "queue_running": [[1, "run-id", {}, {}, "client"]],
                "queue_pending": [[2, "pending-id", {}, {}, "client"], [3, "later-id", {}, {}, "client"]],
            },
        )

    client = _client(httpx.MockTransport(handler))
    try:
        queue = await client.queue()
        assert (queue.running, queue.pending) == (1, 2)
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_reconcile_uses_queue_membership_when_history_has_no_entry() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/history/pending-id":
            return httpx.Response(200, json={})
        if request.url.path == "/queue":
            return httpx.Response(
                200,
                json={"queue_running": [], "queue_pending": [[1, "pending-id", {}, {}, "client"]]},
            )
        raise AssertionError(f"unexpected request {request.method} {request.url}")

    client = _client(httpx.MockTransport(handler))
    try:
        observation = await client.reconcile(type("Handle", (), {"internal_id": "pending-id"})())
        assert observation.status is JobObservationStatus.QUEUED
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_history_error_is_safe_and_does_not_leak_engine_payload() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "engine-secret-123": {
                    "status": {
                        "status_str": "error",
                        "messages": [["execution_error", {"exception_message": "/private/secret/path"}]],
                    }
                }
            },
        )

    client = _client(httpx.MockTransport(handler))
    try:
        observation = await client.reconcile(type("Handle", (), {"internal_id": "engine-secret-123"})())
        assert observation.status is JobObservationStatus.FAILED
        assert observation.error_code == "generation_failed"
        assert observation.safe_message == "Generation failed"
        assert "/private/secret/path" not in repr(observation)
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_websocket_disconnect_returns_unknown_without_resubmission() -> None:
    class DisconnectingSocket:
        async def __aenter__(self) -> "DisconnectingSocket":
            return self

        async def __aexit__(self, *_args: Any) -> None:
            return None

        async def recv(self) -> str:
            raise ConnectionError("socket disconnected")

    def connect(_url: str, **_kwargs: Any) -> DisconnectingSocket:
        return DisconnectingSocket()

    async def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError(f"unexpected HTTP request {request.method} {request.url}")

    client = _client(httpx.MockTransport(handler))
    client._websocket_connect = connect
    try:
        observation = await client.watch(type("Handle", (), {"internal_id": "engine-secret-123"})())
        assert observation.status is JobObservationStatus.UNKNOWN
        assert observation.error_code == "engine_disconnect"
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_http_timeout_maps_to_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    async def timeout(*_args: Any, **_kwargs: Any) -> httpx.Response:
        raise httpx.ReadTimeout("timed out")

    async def handler(request: httpx.Request) -> httpx.Response:
        return await timeout(request)

    client = _client(httpx.MockTransport(handler))
    try:
        observation = await client.reconcile(type("Handle", (), {"internal_id": "engine-secret-123"})())
        assert observation.status is JobObservationStatus.UNKNOWN
        assert observation.error_code == "generation_timeout"
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_restart_reconciliation_does_not_submit_again() -> None:
    calls: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(f"{request.method} {request.url.path}")
        if request.url.path == "/history/existing-id":
            return httpx.Response(200, json={"existing-id": {"status": {"status_str": "running"}}})
        raise AssertionError("reconciliation must not submit a new prompt")

    client = _client(httpx.MockTransport(handler))
    try:
        observation = await client.reconcile(type("Handle", (), {"internal_id": "existing-id"})())
        assert observation.status is JobObservationStatus.PROCESSING
        assert calls == ["GET /history/existing-id"]
    finally:
        await client.aclose()


def test_comfy_client_rejects_non_loopback_base_url() -> None:
    with pytest.raises(ValueError, match="loopback"):
        ComfyClient("http://192.168.1.50:8188")
