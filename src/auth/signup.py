"""Signup and login endpoints for the Cyphergy platform.

POST /api/v1/auth/signup -- Create account, return JWT
POST /api/v1/auth/login  -- Authenticate, return JWT

Password hashing uses bcrypt. JWTs are created via JWTHandler.
All configuration from environment variables (CPAA-compliant).
"""

from __future__ import annotations

import logging
import re

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.jwt_handler import JWTHandler
from src.database.crud import create_user, get_user_by_email
from src.database.engine import get_db

logger = logging.getLogger("cyphergy.auth.signup")

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

# Minimum password length for legal platform security
_MIN_PASSWORD_LENGTH = 10


class SignupRequest(BaseModel):
    """Signup request body."""

    email: EmailStr
    password: str = Field(
        ...,
        min_length=_MIN_PASSWORD_LENGTH,
        description=f"Password (min {_MIN_PASSWORD_LENGTH} characters, must contain uppercase, lowercase, and a digit).",
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=256,
        description="Display name.",
    )


class LoginRequest(BaseModel):
    """Login request body."""

    email: EmailStr
    password: str = Field(
        ...,
        min_length=1,
        description="Account password.",
    )


class AuthResponse(BaseModel):
    """Authentication response with JWT token."""

    token: str
    token_type: str = "bearer"
    email: str
    name: str


# ---------------------------------------------------------------------------
# Password utilities
# ---------------------------------------------------------------------------


def _validate_password_strength(password: str) -> None:
    """Enforce password complexity requirements.

    Requirements:
        - Minimum 10 characters (enforced by Pydantic min_length too)
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit

    Raises:
        HTTPException: If the password does not meet requirements.
    """
    if len(password) < _MIN_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Password must be at least {_MIN_PASSWORD_LENGTH} characters.",
        )
    if not re.search(r"[A-Z]", password):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must contain at least one uppercase letter.",
        )
    if not re.search(r"[a-z]", password):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must contain at least one lowercase letter.",
        )
    if not re.search(r"\d", password):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must contain at least one digit.",
        )


def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt.

    Args:
        password: The plaintext password.

    Returns:
        The bcrypt hash string.
    """
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a plaintext password against a bcrypt hash.

    Args:
        password: The plaintext password to check.
        password_hash: The stored bcrypt hash.

    Returns:
        True if the password matches, False otherwise.
    """
    return bcrypt.checkpw(
        password.encode("utf-8"),
        password_hash.encode("utf-8"),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/signup",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new account",
)
async def signup(
    body: SignupRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    """Register a new user account.

    Validates password strength, checks for email uniqueness, hashes
    the password with bcrypt, creates the user record, and returns
    a signed JWT for immediate authentication.
    """
    _validate_password_strength(body.password)

    # Check if email is already registered
    existing = await get_user_by_email(db, email=body.email)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    # Hash password and create user
    hashed = hash_password(body.password)
    user = await create_user(
        db,
        email=body.email,
        password_hash=hashed,
        name=body.name,
    )

    # Issue JWT
    jwt_handler = JWTHandler()
    token = jwt_handler.create_token(
        payload={
            "sub": str(user.id),
            "email": user.email,
            "name": user.name,
        }
    )

    logger.info("user_signup | user_id=%s", user.id)

    return AuthResponse(
        token=token,
        email=user.email,
        name=user.name,
    )


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Authenticate and receive a JWT",
)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    """Authenticate with email and password.

    Looks up the user by email, verifies the bcrypt password hash,
    and returns a signed JWT on success. Returns 401 on invalid
    credentials (deliberately vague to avoid user enumeration).
    """
    user = await get_user_by_email(db, email=body.email)

    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Contact support.",
        )

    # Issue JWT
    jwt_handler = JWTHandler()
    token = jwt_handler.create_token(
        payload={
            "sub": str(user.id),
            "email": user.email,
            "name": user.name,
        }
    )

    logger.info("user_login | user_id=%s", user.id)

    return AuthResponse(
        token=token,
        email=user.email,
        name=user.name,
    )
