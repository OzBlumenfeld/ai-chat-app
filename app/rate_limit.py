from typing import Union, Callable, Awaitable

import jwt
from pyrate_limiter import Duration, Limiter, Rate
from fastapi import HTTPException, Request
from starlette.websockets import WebSocket

from app.config import settings


async def ip_identifier(request: Union[Request, WebSocket]) -> str:
    """Rate-limit key based on client IP + path (for unauthenticated endpoints)."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    elif request.client:
        ip = request.client.host
    else:
        ip = "127.0.0.1"
    return f"{ip}:{request.scope['path']}"


async def user_identifier(request: Union[Request, WebSocket]) -> str:
    """Rate-limit key based on authenticated user ID + path.

    Falls back to IP if the token is missing or invalid (the auth dependency
    will still reject the request separately).
    """
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        try:
            payload = jwt.decode(
                token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
            )
            return f"user:{payload['user_id']}:{request.scope['path']}"
        except jwt.PyJWTError:
            pass
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    elif request.client:
        ip = request.client.host
    else:
        ip = "127.0.0.1"
    return f"{ip}:{request.scope['path']}"


class _InMemoryRateLimiter:
    """FastAPI dependency for in-memory rate limiting using pyrate_limiter."""

    def __init__(
        self,
        limiter: Limiter,
        identifier: Callable[[Union[Request, WebSocket]], Awaitable[str]],
    ) -> None:
        self._limiter = limiter
        self._identifier = identifier

    async def __call__(self, request: Request) -> None:
        key = await self._identifier(request)
        acquired = self._limiter.try_acquire(key, blocking=False)
        if not acquired:
            raise HTTPException(status_code=429, detail="Too many requests")


# ---- Per-endpoint limiters -----------------------------------------------

# 5 login attempts per minute per IP  — brute-force protection
login_rate_limiter = _InMemoryRateLimiter(
    Limiter(Rate(5, Duration.MINUTE)),
    ip_identifier,
)

# 3 registration attempts per minute per IP — prevent mass account creation
register_rate_limiter = _InMemoryRateLimiter(
    Limiter(Rate(3, Duration.MINUTE)),
    ip_identifier,
)

# 20 RAG queries per minute per user — LLM cost protection
query_rate_limiter = _InMemoryRateLimiter(
    Limiter(Rate(20, Duration.MINUTE)),
    user_identifier,
)

# 10 uploads per minute per user — storage abuse prevention
upload_rate_limiter = _InMemoryRateLimiter(
    Limiter(Rate(10, Duration.MINUTE)),
    user_identifier,
)
