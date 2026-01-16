"""
Username/Password Authentication with Telegram Verification

Issue #750: Заменяет Telegram Login Widget на классическую авторизацию
с верификацией через бота.

Флоу регистрации:
1. POST /register/init - создаёт verification record
2. Пользователь пишет /start боту → бот отправляет 6-значный код
3. POST /register/verify - проверяет код и создаёт аккаунт

Флоу сброса пароля:
1. POST /reset-password/init - создаёт verification record
2. Бот отправляет код сброса
3. POST /reset-password/verify - проверяет код и меняет пароль
"""

import hashlib
import hmac
import logging
import os
import secrets
import time
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from src.core.http_client import get_http_client
from src.core.supabase import get_supabase


logger = logging.getLogger(__name__)
router = APIRouter()

# Constants
VERIFICATION_CODE_LENGTH = 6
VERIFICATION_EXPIRY_MINUTES = 15
PASSWORD_MIN_LENGTH = 8


# --- Pydantic Models ---


class RegisterInitRequest(BaseModel):
    """Request to start registration."""

    telegram_username: str = Field(..., description="Telegram username without @")

    @field_validator("telegram_username")
    @classmethod
    def normalize_username(cls, v: str) -> str:
        """Remove @ prefix if present and lowercase."""
        return v.lstrip("@").lower()


class RegisterInitResponse(BaseModel):
    """Response with verification ID."""

    verification_id: str
    message: str


class RegisterVerifyRequest(BaseModel):
    """Request to complete registration."""

    verification_id: str = Field(..., description="UUID from register/init")
    code: str = Field(..., description="6-digit verification code")
    password: str = Field(..., min_length=PASSWORD_MIN_LENGTH, description="User password")


class LoginRequest(BaseModel):
    """Login request."""

    telegram_username: str = Field(..., description="Telegram username without @")
    password: str = Field(..., description="User password")

    @field_validator("telegram_username")
    @classmethod
    def normalize_username(cls, v: str) -> str:
        """Remove @ prefix if present and lowercase."""
        return v.lstrip("@").lower()


class ResetPasswordInitRequest(BaseModel):
    """Request to start password reset."""

    telegram_username: str = Field(..., description="Telegram username without @")

    @field_validator("telegram_username")
    @classmethod
    def normalize_username(cls, v: str) -> str:
        """Remove @ prefix if present and lowercase."""
        return v.lstrip("@").lower()


class ResetPasswordVerifyRequest(BaseModel):
    """Request to complete password reset."""

    telegram_username: str = Field(..., description="Telegram username without @")
    code: str = Field(..., description="6-digit verification code")
    new_password: str = Field(..., min_length=PASSWORD_MIN_LENGTH, description="New password")

    @field_validator("telegram_username")
    @classmethod
    def normalize_username(cls, v: str) -> str:
        """Remove @ prefix if present and lowercase."""
        return v.lstrip("@").lower()


class AuthResponse(BaseModel):
    """Auth response with access token."""

    success: bool
    access_token: Optional[str] = None
    user: Optional[dict] = None
    error: Optional[str] = None


# --- Helper Functions ---


def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against bcrypt hash."""
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def generate_access_token(buyer_id: str) -> str:
    """
    Generate simple access token.
    Format: buyer_id:timestamp:signature
    """
    api_key = os.getenv("API_KEY", "")
    token_data = f"{buyer_id}:{int(time.time())}"
    signature = hmac.new(api_key.encode(), token_data.encode(), hashlib.sha256).hexdigest()[:16]
    return f"{token_data}:{signature}"


def generate_verification_code() -> str:
    """Generate 6-digit verification code."""
    return "".join(secrets.choice("0123456789") for _ in range(VERIFICATION_CODE_LENGTH))


# --- API Endpoints ---


@router.post(
    "/register/init",
    response_model=RegisterInitResponse,
    summary="Start registration process",
    description="Create verification record. User must then send /start to @UniAiHelper_bot.",
)
async def register_init(data: RegisterInitRequest) -> RegisterInitResponse:
    """
    Start registration process.

    1. Check that username is not already registered
    2. Create verification record (without code - code is generated when user writes /start)
    3. Return verification_id

    User must then write /start to @UniAiHelper_bot to receive the code.
    """
    sb = get_supabase()
    client = get_http_client()

    # Check if username is already registered
    response = await client.get(
        f"{sb.rest_url}/buyers",
        headers=sb.get_headers(),
        params={
            "select": "id",
            "telegram_username": f"eq.{data.telegram_username}",
            "limit": "1",
        },
    )

    if response.status_code != 200:
        logger.error(f"DB error checking username: {response.status_code}")
        raise HTTPException(status_code=500, detail="Database error")

    if response.json():
        raise HTTPException(
            status_code=400, detail="Username already registered. Use login instead."
        )

    # Check for existing pending verification
    response = await client.get(
        f"{sb.rest_url}/verification_codes",
        headers=sb.get_headers(),
        params={
            "select": "id",
            "telegram_username": f"eq.{data.telegram_username}",
            "type": "eq.registration",
            "verified_at": "is.null",
            "expires_at": f"gt.{datetime.utcnow().isoformat()}",
            "limit": "1",
        },
    )

    if response.status_code == 200 and response.json():
        existing = response.json()[0]
        return RegisterInitResponse(
            verification_id=existing["id"],
            message=f"Verification already pending. Send /start to @UniAiHelper_bot from account @{data.telegram_username}",
        )

    # Create verification record
    expires_at = datetime.utcnow() + timedelta(minutes=VERIFICATION_EXPIRY_MINUTES)
    verification_data = {
        "telegram_username": data.telegram_username,
        "type": "registration",
        "expires_at": expires_at.isoformat(),
    }

    response = await client.post(
        f"{sb.rest_url}/verification_codes",
        headers=sb.get_headers(for_write=True),
        json=verification_data,
    )

    if response.status_code not in (200, 201):
        logger.error(f"Failed to create verification: {response.status_code} {response.text}")
        raise HTTPException(status_code=500, detail="Failed to create verification")

    result = response.json()
    verification_id = result[0]["id"] if isinstance(result, list) else result["id"]

    logger.info(f"Created verification for @{data.telegram_username}: {verification_id}")

    return RegisterInitResponse(
        verification_id=verification_id,
        message=f"Send /start to @UniAiHelper_bot from account @{data.telegram_username}",
    )


@router.post(
    "/register/verify",
    response_model=AuthResponse,
    summary="Complete registration with verification code",
    description="Verify code and create user account.",
)
async def register_verify(data: RegisterVerifyRequest) -> AuthResponse:
    """
    Complete registration.

    1. Find verification record by ID
    2. Check code matches
    3. Create buyer account
    4. Mark verification as used
    5. Return access token
    """
    sb = get_supabase()
    client = get_http_client()

    # Find verification record
    response = await client.get(
        f"{sb.rest_url}/verification_codes",
        headers=sb.get_headers(),
        params={
            "select": "*",
            "id": f"eq.{data.verification_id}",
            "type": "eq.registration",
            "verified_at": "is.null",
            "limit": "1",
        },
    )

    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Database error")

    verifications = response.json()
    if not verifications:
        return AuthResponse(success=False, error="Verification not found or already used")

    verification = verifications[0]

    # Check expiry
    expires_at = datetime.fromisoformat(verification["expires_at"].replace("Z", "+00:00"))
    if expires_at < datetime.now(expires_at.tzinfo):
        return AuthResponse(success=False, error="Verification code expired")

    # Check if code was generated (user wrote /start)
    if not verification.get("code"):
        return AuthResponse(
            success=False,
            error=f"Code not yet generated. Send /start to @UniAiHelper_bot from @{verification['telegram_username']}",
        )

    # Check code
    if not secrets.compare_digest(verification["code"], data.code):
        return AuthResponse(success=False, error="Invalid verification code")

    # Check telegram_id was captured
    if not verification.get("telegram_id"):
        return AuthResponse(success=False, error="Telegram ID not captured. Try /start again.")

    # Create buyer account
    password_hash = hash_password(data.password)
    buyer_data = {
        "telegram_username": verification["telegram_username"],
        "telegram_id": str(verification["telegram_id"]),
        "name": verification["telegram_username"],  # Default name to username
        "password_hash": password_hash,
        "status": "active",
    }

    response = await client.post(
        f"{sb.rest_url}/buyers",
        headers=sb.get_headers(for_write=True),
        json=buyer_data,
    )

    if response.status_code not in (200, 201):
        logger.error(f"Failed to create buyer: {response.status_code} {response.text}")
        raise HTTPException(status_code=500, detail="Failed to create account")

    buyer = response.json()[0] if isinstance(response.json(), list) else response.json()

    # Mark verification as used
    await client.patch(
        f"{sb.rest_url}/verification_codes",
        headers=sb.get_headers(for_write=True),
        params={"id": f"eq.{data.verification_id}"},
        json={"verified_at": datetime.utcnow().isoformat()},
    )

    # Generate access token
    access_token = generate_access_token(buyer["id"])

    logger.info(f"User registered: @{verification['telegram_username']} -> {buyer['id']}")

    return AuthResponse(
        success=True,
        access_token=access_token,
        user={
            "id": buyer["id"],
            "telegram_username": buyer["telegram_username"],
            "name": buyer["name"],
        },
    )


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Login with username and password",
    description="Authenticate user with telegram username and password.",
)
async def login(data: LoginRequest) -> AuthResponse:
    """
    Login with username/password.

    1. Find buyer by telegram_username
    2. Verify password
    3. Return access token
    """
    sb = get_supabase()
    client = get_http_client()

    # Find buyer
    response = await client.get(
        f"{sb.rest_url}/buyers",
        headers=sb.get_headers(),
        params={
            "select": "id,telegram_username,name,password_hash,status",
            "telegram_username": f"eq.{data.telegram_username}",
            "limit": "1",
        },
    )

    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Database error")

    buyers = response.json()
    if not buyers:
        return AuthResponse(success=False, error="Invalid username or password")

    buyer = buyers[0]

    # Check status
    if buyer.get("status") == "blocked":
        return AuthResponse(success=False, error="Account is blocked")

    # Check password
    if not buyer.get("password_hash"):
        return AuthResponse(
            success=False,
            error="Account not set up for password login. Please register again.",
        )

    if not verify_password(data.password, buyer["password_hash"]):
        return AuthResponse(success=False, error="Invalid username or password")

    # Generate access token
    access_token = generate_access_token(buyer["id"])

    logger.info(f"User logged in: @{data.telegram_username}")

    return AuthResponse(
        success=True,
        access_token=access_token,
        user={
            "id": buyer["id"],
            "telegram_username": buyer["telegram_username"],
            "name": buyer["name"],
        },
    )


@router.post(
    "/reset-password/init",
    response_model=RegisterInitResponse,
    summary="Start password reset",
    description="Create verification record for password reset.",
)
async def reset_password_init(data: ResetPasswordInitRequest) -> RegisterInitResponse:
    """
    Start password reset process.

    1. Check that user exists
    2. Create verification record
    3. User must write /start to bot to get code
    """
    sb = get_supabase()
    client = get_http_client()

    # Check if user exists
    response = await client.get(
        f"{sb.rest_url}/buyers",
        headers=sb.get_headers(),
        params={
            "select": "id,telegram_id",
            "telegram_username": f"eq.{data.telegram_username}",
            "limit": "1",
        },
    )

    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Database error")

    buyers = response.json()
    if not buyers:
        # Don't reveal if user exists or not
        return RegisterInitResponse(
            verification_id="",
            message=f"If account exists, send /start to @UniAiHelper_bot from @{data.telegram_username}",
        )

    # Check for existing pending reset
    response = await client.get(
        f"{sb.rest_url}/verification_codes",
        headers=sb.get_headers(),
        params={
            "select": "id",
            "telegram_username": f"eq.{data.telegram_username}",
            "type": "eq.password_reset",
            "verified_at": "is.null",
            "expires_at": f"gt.{datetime.utcnow().isoformat()}",
            "limit": "1",
        },
    )

    if response.status_code == 200 and response.json():
        existing = response.json()[0]
        return RegisterInitResponse(
            verification_id=existing["id"],
            message=f"Reset already pending. Send /start to @UniAiHelper_bot from @{data.telegram_username}",
        )

    # Create verification record
    expires_at = datetime.utcnow() + timedelta(minutes=VERIFICATION_EXPIRY_MINUTES)
    verification_data = {
        "telegram_username": data.telegram_username,
        "telegram_id": int(buyers[0]["telegram_id"]) if buyers[0].get("telegram_id") else None,
        "type": "password_reset",
        "expires_at": expires_at.isoformat(),
    }

    response = await client.post(
        f"{sb.rest_url}/verification_codes",
        headers=sb.get_headers(for_write=True),
        json=verification_data,
    )

    if response.status_code not in (200, 201):
        logger.error(f"Failed to create reset verification: {response.status_code}")
        raise HTTPException(status_code=500, detail="Failed to initiate reset")

    result = response.json()
    verification_id = result[0]["id"] if isinstance(result, list) else result["id"]

    logger.info(f"Created password reset for @{data.telegram_username}")

    return RegisterInitResponse(
        verification_id=verification_id,
        message=f"Send /start to @UniAiHelper_bot from @{data.telegram_username}",
    )


@router.post(
    "/reset-password/verify",
    response_model=AuthResponse,
    summary="Complete password reset",
    description="Verify code and set new password.",
)
async def reset_password_verify(data: ResetPasswordVerifyRequest) -> AuthResponse:
    """
    Complete password reset.

    1. Find verification by username and type
    2. Check code
    3. Update password
    4. Return access token
    """
    sb = get_supabase()
    client = get_http_client()

    # Find verification record
    response = await client.get(
        f"{sb.rest_url}/verification_codes",
        headers=sb.get_headers(),
        params={
            "select": "*",
            "telegram_username": f"eq.{data.telegram_username}",
            "type": "eq.password_reset",
            "verified_at": "is.null",
            "order": "created_at.desc",
            "limit": "1",
        },
    )

    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Database error")

    verifications = response.json()
    if not verifications:
        return AuthResponse(success=False, error="No pending password reset")

    verification = verifications[0]

    # Check expiry
    expires_at = datetime.fromisoformat(verification["expires_at"].replace("Z", "+00:00"))
    if expires_at < datetime.now(expires_at.tzinfo):
        return AuthResponse(success=False, error="Reset code expired")

    # Check code
    if not verification.get("code"):
        return AuthResponse(
            success=False,
            error=f"Code not yet generated. Send /start to @UniAiHelper_bot from @{data.telegram_username}",
        )

    if not secrets.compare_digest(verification["code"], data.code):
        return AuthResponse(success=False, error="Invalid verification code")

    # Update password
    password_hash = hash_password(data.new_password)
    response = await client.patch(
        f"{sb.rest_url}/buyers",
        headers=sb.get_headers(for_write=True),
        params={"telegram_username": f"eq.{data.telegram_username}"},
        json={"password_hash": password_hash},
    )

    if response.status_code not in (200, 204):
        logger.error(f"Failed to update password: {response.status_code}")
        raise HTTPException(status_code=500, detail="Failed to update password")

    # Mark verification as used
    await client.patch(
        f"{sb.rest_url}/verification_codes",
        headers=sb.get_headers(for_write=True),
        params={"id": f"eq.{verification['id']}"},
        json={"verified_at": datetime.utcnow().isoformat()},
    )

    # Get updated buyer for token
    response = await client.get(
        f"{sb.rest_url}/buyers",
        headers=sb.get_headers(),
        params={
            "select": "id,telegram_username,name",
            "telegram_username": f"eq.{data.telegram_username}",
            "limit": "1",
        },
    )

    buyers = response.json() if response.status_code == 200 else []
    if not buyers:
        return AuthResponse(success=True, error="Password updated but login failed")

    buyer = buyers[0]
    access_token = generate_access_token(buyer["id"])

    logger.info(f"Password reset completed for @{data.telegram_username}")

    return AuthResponse(
        success=True,
        access_token=access_token,
        user={
            "id": buyer["id"],
            "telegram_username": buyer["telegram_username"],
            "name": buyer["name"],
        },
    )
