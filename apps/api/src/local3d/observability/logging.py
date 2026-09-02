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
    """Log only the safe correlation fields; ``details`` is intentionally ignored."""

    logger.info(
        "job_id=%s event=%s message=%s",
        str(job_id),
        event_type,
        safe_message,
        extra={"job_id": str(job_id), "event_type": event_type},
    )
