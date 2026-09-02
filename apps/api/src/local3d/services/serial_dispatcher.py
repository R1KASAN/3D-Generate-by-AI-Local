from __future__ import annotations

from collections import deque


class SerialDispatcher:
    """Small in-process FIFO gate for the single GPU execution resource."""

    def __init__(self) -> None:
        self._queue: deque[str] = deque()
        self.active_job: str | None = None

    @property
    def pending(self) -> tuple[str, ...]:
        return tuple(self._queue)

    def enqueue(self, job_id: str) -> bool:
        if job_id == self.active_job or job_id in self._queue:
            return False
        self._queue.append(job_id)
        return True

    def claim_next(self) -> str | None:
        if self.active_job is not None or not self._queue:
            return None
        self.active_job = self._queue.popleft()
        return self.active_job

    def complete(self, job_id: str) -> None:
        if self.active_job != job_id:
            raise ValueError("only the active job can complete")
        self.active_job = None

    def position(self, job_id: str) -> int | None:
        if job_id == self.active_job:
            return 1
        try:
            return self._queue.index(job_id) + (2 if self.active_job is not None else 1)
        except ValueError:
            return None
