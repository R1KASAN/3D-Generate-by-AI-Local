from __future__ import annotations

import logging
from typing import Any
from uuid import UUID


class _StructuredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return (
            f"job_id={getattr(record, 'job_id', '-') } "
            f"event={getattr(record, 'event_type', record.name)} "
            f"message={record.getMessage()}"
        )


_SAFE_DETAIL_KEYS = frozenset(
    {"request_id", "duration_ms", "failure_category", "from_state", "to_state", "queue_position"}
)


def configure_logging(name: str = "local3d") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = True
    if not any(isinstance(handler, logging.StreamHandler) for handler in logger.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(_StructuredFormatter())
        logger.addHandler(handler)
    return logger


def log_job_event(
    logger: logging.Logger,
    *,
    job_id: UUID | str,
    event_type: str,
    safe_message: str,
    details: dict[str, Any] | None = None,
) -> None:
    """Log allowlisted diagnostic fields while dropping content and credentials."""

    safe_details: list[str] = []
    for key in sorted(_SAFE_DETAIL_KEYS):
        if not details or key not in details:
            continue
        value = details[key]
        if isinstance(value, (str, int, float, bool)):
            safe_details.append(f"{key}={value}")
    suffix = " " + " ".join(safe_details) if safe_details else ""

    logger.info(
        "job_id=%s event=%s message=%s%s",
        str(job_id),
        event_type,
        safe_message,
        suffix,
        extra={"job_id": str(job_id), "event_type": event_type},
    )
