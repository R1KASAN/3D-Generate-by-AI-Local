from __future__ import annotations

import asyncio
import ipaddress
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit
from uuid import uuid4

import httpx
import websockets

from .base import EngineHandle, EngineObservation, JobObservationStatus


class ComfyClientError(RuntimeError):
    """Raised when a ComfyUI response cannot be safely interpreted."""

    def __init__(self, message: str, *, code: str = "engine_unavailable") -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class QueueSnapshot:
    running: int
    pending: int
    running_ids: tuple[str, ...] = ()
    pending_ids: tuple[str, ...] = ()


WebSocketConnect = Callable[..., Any]


class ComfyClient:
    """Loopback-only ComfyUI client; engine identifiers stay adapter-private."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8188",
        *,
        http_client: httpx.AsyncClient | None = None,
        websocket_connect: WebSocketConnect | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        self.base_url = _validate_loopback_url(base_url)
        self._http = http_client or httpx.AsyncClient(base_url=self.base_url)
        self._owns_http = http_client is None
        self._timeout = timeout_seconds
        self._client_id = uuid4().hex
        self._websocket_connect: WebSocketConnect = websocket_connect or websockets.connect

    async def aclose(self) -> None:
        if self._owns_http:
            await self._http.aclose()

    async def submit(self, workflow: Mapping[str, Any]) -> EngineHandle:
        payload: dict[str, Any] = {"prompt": workflow, "client_id": self._client_id}
        try:
            response = await self._http.post("/prompt", json=payload, timeout=self._timeout)
            response.raise_for_status()
            body = response.json()
        except (httpx.TimeoutException, asyncio.TimeoutError) as exc:
            raise ComfyClientError("ComfyUI submission timed out") from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise ComfyClientError("ComfyUI submission failed") from exc

        prompt_id = body.get("prompt_id") if isinstance(body, dict) else None
        if not isinstance(prompt_id, str) or not prompt_id:
            raise ComfyClientError("ComfyUI returned no execution handle")
        return EngineHandle(internal_id=prompt_id)

    async def upload_image(self, path: Path, *, subfolder: str = "") -> str:
        """Upload a local image to ComfyUI's input area; return its server-side name."""

        try:
            data = path.read_bytes()
        except OSError as exc:
            raise ComfyClientError("input image could not be read") from exc
        files = {"image": (path.name, data)}
        payload: dict[str, Any] = {"overwrite": "true"}
        if subfolder:
            payload["subfolder"] = subfolder
        try:
            response = await self._http.post(
                "/upload/image", files=files, data=payload, timeout=self._timeout
            )
            response.raise_for_status()
            body = response.json()
        except (httpx.TimeoutException, asyncio.TimeoutError) as exc:
            raise ComfyClientError("ComfyUI upload timed out") from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise ComfyClientError("ComfyUI upload failed") from exc

        name = body.get("name") if isinstance(body, dict) else None
        if not isinstance(name, str) or not name:
            raise ComfyClientError("ComfyUI returned no uploaded image name")
        return name

    async def queue(self) -> QueueSnapshot:
        body = await self._get_json("/queue")
        if not isinstance(body, dict):
            raise ComfyClientError("ComfyUI queue response is invalid")
        running = body.get("queue_running", [])
        pending = body.get("queue_pending", [])
        if not isinstance(running, list) or not isinstance(pending, list):
            raise ComfyClientError("ComfyUI queue response is invalid")
        return QueueSnapshot(
            running=len(running),
            pending=len(pending),
            running_ids=_queue_ids(running),
            pending_ids=_queue_ids(pending),
        )

    async def reconcile(self, handle: EngineHandle) -> EngineObservation:
        prompt_id = _internal_id(handle)
        try:
            body = await self._get_json(f"/history/{quote(prompt_id, safe='')}")
        except ComfyClientError as exc:
            if exc.code == "not_found":
                body = {}
            elif exc.code == "generation_timeout":
                return EngineObservation(
                    status=JobObservationStatus.UNKNOWN,
                    error_code="generation_timeout",
                    safe_message="Generation status is unavailable",
                )
            elif exc.code == "engine_disconnect":
                return EngineObservation(
                    status=JobObservationStatus.UNKNOWN,
                    error_code="engine_disconnect",
                    safe_message="Generation status is unavailable",
                )
            else:
                raise

        if isinstance(body, dict) and prompt_id in body:
            return _observation_from_history(body[prompt_id])

        snapshot = await self.queue()
        # Queue entries are opaque engine data; only membership is used.
        if _queue_contains(snapshot, prompt_id, body):
            return EngineObservation(status=JobObservationStatus.QUEUED)
        return EngineObservation(
            status=JobObservationStatus.UNKNOWN,
            error_code="unknown_execution",
            safe_message="Generation status is unavailable",
        )

    async def watch(self, handle: EngineHandle) -> EngineObservation:
        prompt_id = _internal_id(handle)
        ws_url = _websocket_url(self.base_url, self._client_id)
        try:
            async with self._websocket_connect(ws_url) as socket:
                while True:
                    raw_message = await socket.recv()
                    message = _decode_message(raw_message)
                    if not isinstance(message, dict):
                        continue
                    data = message.get("data")
                    if not isinstance(data, dict) or data.get("prompt_id") != prompt_id:
                        continue
                    message_type = message.get("type")
                    if message_type == "progress":
                        value = data.get("value")
                        maximum = data.get("max")
                        percent = _percent(value, maximum)
                        return EngineObservation(
                            status=JobObservationStatus.PROCESSING,
                            progress_percent=percent,
                        )
                    if message_type == "executing" and data.get("node") is None:
                        return EngineObservation(status=JobObservationStatus.SUCCEEDED)
                    if message_type in {"execution_error", "execution_interrupted"}:
                        return EngineObservation(
                            status=JobObservationStatus.FAILED,
                            error_code="generation_failed",
                            safe_message="Generation failed",
                        )
        except (ConnectionError, OSError, asyncio.TimeoutError, websockets.WebSocketException):
            return EngineObservation(
                status=JobObservationStatus.UNKNOWN,
                error_code="engine_disconnect",
                safe_message="Generation status is unavailable",
            )

    async def cancel(self, handle: EngineHandle) -> EngineObservation:
        prompt_id = _internal_id(handle)
        try:
            response = await self._http.post(
                "/interrupt", json={"prompt_id": prompt_id}, timeout=self._timeout
            )
            response.raise_for_status()
        except (httpx.HTTPError, asyncio.TimeoutError) as exc:
            raise ComfyClientError("ComfyUI cancellation failed") from exc
        return EngineObservation(
            status=JobObservationStatus.CANCELLED,
            error_code="generation_cancelled",
            safe_message="Generation was cancelled",
        )

    async def _get_json(self, path: str) -> Any:
        try:
            response = await self._http.get(path, timeout=self._timeout)
            if response.status_code == 404:
                raise ComfyClientError("ComfyUI resource was not found", code="not_found")
            response.raise_for_status()
            return response.json()
        except (httpx.ReadTimeout, httpx.ConnectTimeout, asyncio.TimeoutError) as exc:
            raise ComfyClientError("ComfyUI request timed out", code="generation_timeout") from exc
        except (httpx.ConnectError, httpx.RemoteProtocolError) as exc:
            raise ComfyClientError("ComfyUI connection failed", code="engine_disconnect") from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise ComfyClientError("ComfyUI request failed") from exc


def _validate_loopback_url(base_url: str) -> str:
    parsed = urlsplit(base_url)
    hostname = parsed.hostname
    if (
        parsed.scheme not in {"http", "https"}
        or hostname is None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("ComfyUI base URL must be loopback HTTP(S)")
    normalized = hostname.rstrip(".").lower()
    try:
        loopback = ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        loopback = normalized == "localhost"
    if not loopback:
        raise ValueError("ComfyUI base URL must be loopback")
    return base_url.rstrip("/")


def _websocket_url(base_url: str, client_id: str) -> str:
    parsed = urlsplit(base_url)
    scheme = "wss" if parsed.scheme == "https" else "ws"
    return urlunsplit((scheme, parsed.netloc, "/ws", f"clientId={quote(client_id)}", ""))


def _internal_id(handle: EngineHandle) -> str:
    internal_id = getattr(handle, "internal_id", None)
    if not isinstance(internal_id, str) or not internal_id:
        raise ComfyClientError("execution handle is invalid")
    return internal_id


def _observation_from_history(entry: Any) -> EngineObservation:
    if not isinstance(entry, dict):
        return EngineObservation(
            status=JobObservationStatus.UNKNOWN,
            error_code="unknown_execution",
            safe_message="Generation status is unavailable",
        )
    status = entry.get("status")
    status_str = status.get("status_str") if isinstance(status, dict) else None
    if status_str in {"success", "completed"}:
        return EngineObservation(
            status=JobObservationStatus.SUCCEEDED,
            candidates=tuple(_history_paths(entry.get("outputs"))),
        )
    if status_str in {"error", "failed"}:
        return EngineObservation(
            status=JobObservationStatus.FAILED,
            error_code="generation_failed",
            safe_message="Generation failed",
        )
    if status_str in {"cancelled", "canceled", "interrupted"}:
        return EngineObservation(
            status=JobObservationStatus.CANCELLED,
            error_code="generation_cancelled",
            safe_message="Generation was cancelled",
        )
    return EngineObservation(
        status=JobObservationStatus.PROCESSING,
        progress_percent=_status_progress(status),
    )


def _history_paths(outputs: Any) -> list[Any]:
    paths: list[Any] = []
    if not isinstance(outputs, dict):
        return paths
    for output in outputs.values():
        if not isinstance(output, dict):
            continue
        for entries in output.values():
            if not isinstance(entries, list):
                continue
            for item in entries:
                if isinstance(item, dict) and isinstance(item.get("filename"), str):
                    paths.append(item["filename"])
    # Paths are adapter-private candidates; the resolver applies containment rules.
    from pathlib import Path

    return [Path(path) for path in paths]


def _status_progress(status: Any) -> int | None:
    if not isinstance(status, dict):
        return None
    value = status.get("progress")
    return value if isinstance(value, int) and 0 <= value <= 100 else None


def _queue_contains(snapshot: QueueSnapshot, prompt_id: str, raw_body: Any) -> bool:
    del raw_body
    return prompt_id in snapshot.running_ids or prompt_id in snapshot.pending_ids


def _queue_ids(entries: list[Any]) -> tuple[str, ...]:
    ids: list[str] = []
    for entry in entries:
        if isinstance(entry, list) and len(entry) > 1 and isinstance(entry[1], str):
            ids.append(entry[1])
    return tuple(ids)


def _decode_message(raw_message: Any) -> Any:
    if isinstance(raw_message, bytes):
        raw_message = raw_message.decode("utf-8", errors="replace")
    if not isinstance(raw_message, str):
        return None
    try:
        return json.loads(raw_message)
    except json.JSONDecodeError:
        return None


def _percent(value: Any, maximum: Any) -> int | None:
    if not isinstance(value, (int, float)) or not isinstance(maximum, (int, float)) or maximum <= 0:
        return None
    percent = round((value / maximum) * 100)
    return max(0, min(100, percent))
