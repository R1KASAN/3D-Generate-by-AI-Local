from __future__ import annotations

from .errors import error_body
from ..services.job_tokens import verify_job_token


def authorize_job(token: str | None, token_digest: str) -> bool:
    """Return only a boolean so callers can map all misses to one 404."""

    if not token:
        return False
    return verify_job_token(token, token_digest)


def uniform_job_not_found() -> dict[str, dict[str, str]]:
    return error_body("job_not_found", "Job not found")
