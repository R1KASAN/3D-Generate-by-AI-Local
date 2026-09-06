"""A stalled ComfyUI status read must not move the job out of `processing`.

ComfyUI serves its HTTP API from the process that runs the graph, so a heavy
GPU step can stall a status read for tens of seconds while the generation
itself is progressing normally. Before the bounded retry in
`ComfyClient._get_json`, the first stalled read became a terminal
`generation_timeout` and discarded real in-flight work. Observed live on
2026-09-06: jobs died at 125s and 194s while others on the same engine
completed at 240s and 306s, which rules out generation duration as the cause.

These tests cover the state-machine half of that fix. They drive the real
`ComfyClient` through the real `GenerationCoordinator` - the same path
`JobService` uses to decide a transition - and assert the job never leaves
`processing` while the retries are happening, and that its state sequence
stays monotonic (FR-022).
"""

from __future__ import annotations

import httpx
import pytest

from local3d.adapters.generation.comfy_client import ComfyClient
from local3d.domain.jobs import JobState
from local3d.services.generation_coordinator import GenerationCoordinator

PROMPT_ID = "engine-secret-123"

# Terminal states the job must never reach while the engine is merely slow.
TERMINAL_STATES = {JobState.FAILED, JobState.COMPLETED, JobState.CANCELLED}


def _handle() -> object:
    return type("Handle", (), {"internal_id": PROMPT_ID})()


def _client(transport: httpx.MockTransport) -> ComfyClient:
    http = httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8188")
    return ComfyClient("http://127.0.0.1:8188", http_client=http)


def _running_queue() -> httpx.Response:
    """ComfyUI reporting our prompt as actively running."""
    return httpx.Response(
        200,
        json={"queue_running": [[1, PROMPT_ID, {}, {}, "client"]], "queue_pending": []},
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("stalls", [1, 2])
async def test_job_stays_processing_through_transient_status_stalls(
    monkeypatch: pytest.MonkeyPatch, stalls: int
) -> None:
    """One or two stalled reads must resolve to PROCESSING, not a failure.

    The decision the service acts on is what matters here: if the coordinator
    ever returns FAILED, the job is written to a terminal state and the GPU
    work is thrown away even though the engine was only busy.
    """
    monkeypatch.setattr(ComfyClient, "STATUS_POLL_BACKOFF_SECONDS", (0.0, 0.0))
    reads = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.startswith("/history/"):
            return httpx.Response(404)
        reads["count"] += 1
        if reads["count"] <= stalls:
            raise httpx.ReadTimeout("engine busy on a GPU step")
        return _running_queue()

    client = _client(httpx.MockTransport(handler))
    try:
        observation = await client.reconcile(_handle())
    finally:
        await client.aclose()

    decision = GenerationCoordinator().decide(observation)
    assert decision.target_state is JobState.PROCESSING, (
        f"{stalls} transient stall(s) moved the job to {decision.target_state} - "
        "in-flight GPU work would have been discarded"
    )
    assert decision.error is None
    assert reads["count"] == stalls + 1, "the stalls must be retried, not surfaced"


@pytest.mark.asyncio
async def test_state_sequence_is_monotonic_across_a_stalled_poll(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Across a whole polling window containing a stall, every decision must be
    PROCESSING - no terminal state, and no regression to QUEUED (FR-022)."""
    monkeypatch.setattr(ComfyClient, "STATUS_POLL_BACKOFF_SECONDS", (0.0, 0.0))
    reads = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.startswith("/history/"):
            return httpx.Response(404)
        reads["count"] += 1
        # Poll 2 of the window stalls once before answering.
        if reads["count"] == 2:
            raise httpx.ReadTimeout("engine busy on a GPU step")
        return _running_queue()

    coordinator = GenerationCoordinator()
    observed: list[JobState] = []
    client = _client(httpx.MockTransport(handler))
    try:
        for _ in range(4):
            observation = await client.reconcile(_handle())
            observed.append(coordinator.decide(observation).target_state)
    finally:
        await client.aclose()

    assert observed == [JobState.PROCESSING] * 4, observed
    assert not TERMINAL_STATES.intersection(observed), (
        "a transient stall must never produce a terminal state"
    )


@pytest.mark.asyncio
async def test_engine_that_never_answers_still_fails_terminally(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The retry must not turn a genuinely dead engine into an unkillable job:
    once the bounded budget is spent, the coordinator still returns FAILED with
    the same safe error code the service handled before this change."""
    monkeypatch.setattr(ComfyClient, "STATUS_POLL_BACKOFF_SECONDS", (0.0, 0.0))

    def handler(request: httpx.Request) -> httpx.Response:
        del request
        raise httpx.ReadTimeout("engine hung")

    client = _client(httpx.MockTransport(handler))
    try:
        observation = await client.reconcile(_handle())
    finally:
        await client.aclose()

    decision = GenerationCoordinator().decide(observation)
    assert decision.target_state is JobState.FAILED
    assert decision.error is not None
    assert decision.error.code == "generation_timeout"
    assert decision.error.message == "Generation status is unavailable"
