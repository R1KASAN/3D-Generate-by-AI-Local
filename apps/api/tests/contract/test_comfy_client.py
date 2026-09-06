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
async def test_reconcile_maps_running_queue_entry_to_processing() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/history/running-id":
            return httpx.Response(200, json={})
        if request.url.path == "/queue":
            return httpx.Response(
                200,
                json={"queue_running": [[1, "running-id", {}, {}, "client"]], "queue_pending": []},
            )
        raise AssertionError(f"unexpected request {request.method} {request.url}")

    client = _client(httpx.MockTransport(handler))
    try:
        observation = await client.reconcile(type("Handle", (), {"internal_id": "running-id"})())
        assert observation.status is JobObservationStatus.PROCESSING
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


@pytest.mark.asyncio
async def test_upload_image_returns_server_side_name(tmp_path: Path) -> None:
    image_path = tmp_path / "input.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\nfake-bytes")

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/upload/image"
        assert b'filename="job-uuid.png"' in request.content
        return httpx.Response(200, json={"name": "input_00001_.png", "subfolder": "", "type": "input"})

    client = _client(httpx.MockTransport(handler))
    try:
        name = await client.upload_image(image_path, filename="job-uuid.png")
        assert name == "input_00001_.png"
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_upload_image_rejects_path_like_override(tmp_path: Path) -> None:
    image_path = tmp_path / "input.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\nfake-bytes")
    client = _client(httpx.MockTransport(lambda _request: httpx.Response(500)))
    try:
        with pytest.raises(Exception, match="upload name is invalid"):
            await client.upload_image(image_path, filename="../other-job.png")
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_upload_image_rejects_missing_name_in_response() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(200, json={"subfolder": ""})

    client = _client(httpx.MockTransport(handler))
    try:
        with pytest.raises(Exception, match="no uploaded image name"):
            await client.upload_image(Path(__file__))
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_ping_returns_true_when_engine_responds() -> None:
    client = _client(httpx.MockTransport(lambda _request: httpx.Response(200, json={"queue_running": []})))
    try:
        assert await client.ping() is True
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_ping_returns_false_on_connection_error_not_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        del request
        raise httpx.ConnectError("connection refused")

    client = _client(httpx.MockTransport(handler))
    try:
        assert await client.ping() is False
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_ping_returns_false_on_timeout_not_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        del request
        raise httpx.ReadTimeout("engine hung")

    client = _client(httpx.MockTransport(handler))
    try:
        assert await client.ping() is False
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_ping_returns_false_on_server_error() -> None:
    client = _client(httpx.MockTransport(lambda _request: httpx.Response(500)))
    try:
        assert await client.ping() is False
    finally:
        await client.aclose()


# --- Bounded retries for transient status-poll timeouts ---------------------
#
# ComfyUI serves its HTTP API from the process running the graph, so a heavy
# GPU step can stall a status read while the generation is progressing fine.
# Observed live 2026-09-06: jobs died at 125s and 194s while others on the
# same engine completed at 240s and 306s, so duration was never the cause -
# a single stalled poll was. These tests pin the retry budget, that only
# timeouts are retried, and that an exhausted budget still fails exactly as
# it did before.


def _timeout_then_success(timeouts: int, body: dict[str, Any]) -> tuple[httpx.MockTransport, list[int]]:
    """Transport that raises ReadTimeout `timeouts` times, then succeeds.
    Returns the transport and a one-element call counter."""
    calls = [0]

    def handler(request: httpx.Request) -> httpx.Response:
        del request
        calls[0] += 1
        if calls[0] <= timeouts:
            raise httpx.ReadTimeout("engine busy")
        return httpx.Response(200, json=body)

    return httpx.MockTransport(handler), calls


@pytest.mark.asyncio
async def test_one_transient_status_timeout_is_retried_and_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ComfyClient, "STATUS_POLL_BACKOFF_SECONDS", (0.0, 0.0))
    transport, calls = _timeout_then_success(1, {"queue_running": [], "queue_pending": []})
    client = _client(transport)
    try:
        snapshot = await client.queue()
    finally:
        await client.aclose()
    assert snapshot.running == 0 and snapshot.pending == 0
    assert calls[0] == 2, "the stalled poll must be retried exactly once before succeeding"


@pytest.mark.asyncio
async def test_two_transient_status_timeouts_are_retried_and_succeed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ComfyClient, "STATUS_POLL_BACKOFF_SECONDS", (0.0, 0.0))
    transport, calls = _timeout_then_success(2, {"queue_running": [], "queue_pending": []})
    client = _client(transport)
    try:
        snapshot = await client.queue()
    finally:
        await client.aclose()
    assert snapshot.pending == 0
    assert calls[0] == 3, "two stalls must both be retried within the budget"


@pytest.mark.asyncio
async def test_exhausted_status_retries_keep_the_existing_timeout_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Once the budget is spent the caller must see exactly the observation it
    saw before this retry existed - an engine that has genuinely stopped
    answering still fails, it is not retried forever."""
    monkeypatch.setattr(ComfyClient, "STATUS_POLL_BACKOFF_SECONDS", (0.0, 0.0))
    calls = [0]

    def handler(request: httpx.Request) -> httpx.Response:
        del request
        calls[0] += 1
        raise httpx.ReadTimeout("engine hung")

    client = _client(httpx.MockTransport(handler))
    try:
        observation = await client.reconcile(
            type("Handle", (), {"internal_id": "engine-secret-123"})()
        )
    finally:
        await client.aclose()

    assert observation.status is JobObservationStatus.UNKNOWN
    assert observation.error_code == "generation_timeout"
    assert observation.safe_message == "Generation status is unavailable"
    assert calls[0] == ComfyClient.STATUS_POLL_RETRIES + 1, (
        "the budget must be bounded - three total reads, then fail"
    )


@pytest.mark.asyncio
async def test_a_404_is_not_retried_as_if_it_were_a_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only timeouts are transient. A history 404 is a real answer meaning the
    prompt is not in history yet, and retrying it would waste the budget and
    delay the queue-membership fallback."""
    monkeypatch.setattr(ComfyClient, "STATUS_POLL_BACKOFF_SECONDS", (0.0, 0.0))
    calls = {"history": 0, "queue": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.startswith("/history/"):
            calls["history"] += 1
            return httpx.Response(404)
        calls["queue"] += 1
        return httpx.Response(
            200,
            json={"queue_running": [[1, "engine-secret-123", {}, {}, "c"]], "queue_pending": []},
        )

    client = _client(httpx.MockTransport(handler))
    try:
        observation = await client.reconcile(
            type("Handle", (), {"internal_id": "engine-secret-123"})()
        )
    finally:
        await client.aclose()

    assert observation.status is JobObservationStatus.PROCESSING
    assert calls["history"] == 1, "a 404 must be accepted on the first response, not retried"
