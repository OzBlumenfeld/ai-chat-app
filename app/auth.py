import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

from app.config import Settings
from app.services.interfaces import AbstractAuthService

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


class AuthService(AbstractAuthService):
    """Concrete authentication service using bcrypt and JWT."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def hash_password(self, password: str) -> str:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def verify_password(self, password: str, hashed: str) -> bool:
        return bcrypt.checkpw(password.encode(), hashed.encode())

    def create_token(self, user_id: uuid.UUID, email: str) -> str:
        payload = {
            "user_id": str(user_id),
            "email": email,
            "exp": datetime.now(timezone.utc) + timedelta(hours=self._settings.JWT_EXPIRY_HOURS),
        }
        return jwt.encode(payload, self._settings.JWT_SECRET, algorithm=self._settings.JWT_ALGORITHM)

    def _decode_token(self, token: str) -> dict[str, Any]:
        """Decode and validate a JWT token."""
        return jwt.decode(token, self._settings.JWT_SECRET, algorithms=[self._settings.JWT_ALGORITHM])


# Module-level singleton
def _create_default() -> AuthService:
    from app.config import settings
    return AuthService(settings=settings)

auth_service = _create_default()


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict[str, Any]:
    """FastAPI dependency — extracts and validates the JWT. Returns user info or raises 401."""
    try:
        payload = auth_service._decode_token(token)
        return {"user_id": uuid.UUID(payload["user_id"]), "email": payload["email"]}
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, KeyError):
        logger.warning("Invalid or expired token")
        raise HTTPException(status_code=401, detail="Invalid or expired token")
