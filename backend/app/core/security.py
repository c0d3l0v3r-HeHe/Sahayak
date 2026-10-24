"""JWT helpers for anonymous device auth, plus an HMAC token for worker-internal calls."""

import hashlib
import hmac
from datetime import UTC, datetime, timedelta

import jwt

from app.core.config import get_settings

ALGORITHM = "HS256"


class AuthError(Exception):
    pass


def create_token(user_id: str) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {"sub": user_id, "iat": now, "exp": now + timedelta(days=settings.jwt_ttl_days)}
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_token(token: str) -> str:
    try:
        payload = jwt.decode(token, get_settings().jwt_secret, algorithms=[ALGORITHM])
    except jwt.PyJWTError as exc:
        raise AuthError("invalid token") from exc
    sub = payload.get("sub")
    if not isinstance(sub, str):
        raise AuthError("invalid token")
    return sub


def internal_token() -> str:
    """Shared secret used by the API to talk to workers (derived from JWT_SECRET)."""
    secret = get_settings().jwt_secret.encode()
    return hmac.new(secret, b"sahayak-internal", hashlib.sha256).hexdigest()


def check_internal_token(token: str | None) -> bool:
    return token is not None and hmac.compare_digest(token, internal_token())
