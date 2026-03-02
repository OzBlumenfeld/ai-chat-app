import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import auth_service, get_current_user
from app.database import get_session
from app.models import User
from app.rate_limit import login_rate_limiter, register_rate_limiter
from app.schemas import RegisterRequest, LoginRequest, AuthResponse, UserResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, dependencies=[Depends(register_rate_limiter)])
async def register(
    body: RegisterRequest, session: AsyncSession = Depends(get_session)
) -> AuthResponse:
    logger.info("Register new user", extra={"email": body.email})
    existing = await session.scalar(select(User).where(User.email == body.email))
    if existing:
        logger.warning("Registration attempt with existing email", extra={"email": body.email})
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(email=body.email, password_hash=auth_service.hash_password(body.password))
    session.add(user)
    await session.commit()
    await session.refresh(user)

    logger.info("User registered", extra={"email": user.email})
    return AuthResponse(token=auth_service.create_token(user.id, user.email), email=user.email)


@router.post("/login", response_model=AuthResponse, dependencies=[Depends(login_rate_limiter)])
async def login(
    body: LoginRequest, session: AsyncSession = Depends(get_session)
) -> AuthResponse:
    user = await session.scalar(select(User).where(User.email == body.email))

    if not user or not auth_service.verify_password(body.password, user.password_hash):
        logger.warning("Failed login attempt", extra={"email": body.email})
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return AuthResponse(token=auth_service.create_token(user.id, user.email), email=user.email)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)) -> UserResponse:
    return UserResponse(email=current_user["email"])
