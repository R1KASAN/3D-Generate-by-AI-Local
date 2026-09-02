from __future__ import annotations

import hashlib
import hmac
import secrets


TOKEN_BYTES = 32


def create_job_token() -> tuple[str, str]:
    """Return a one-time URL-safe capability token and its SHA-256 digest."""

    token = secrets.token_urlsafe(TOKEN_BYTES)
    return token, digest_job_token(token)


def digest_job_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def verify_job_token(token: str, expected_digest: str) -> bool:
    if len(expected_digest) != 64:
        return False
    try:
        int(expected_digest, 16)
    except ValueError:
        return False
    actual_digest = digest_job_token(token)
    return hmac.compare_digest(actual_digest, expected_digest)
