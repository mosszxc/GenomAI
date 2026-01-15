"""
Telegram Login Widget authentication endpoint
"""

import hashlib
import hmac
import os
import time
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import httpx

router = APIRouter()

# Constants
AUTH_DATE_MAX_AGE_SECONDS = 86400  # 24 hours


class TelegramAuthData(BaseModel):
    """Telegram Login Widget auth data"""

    id: int = Field(..., description="Telegram user ID")
    first_name: str = Field(..., description="User's first name")
    last_name: Optional[str] = Field(None, description="User's last name")
    username: Optional[str] = Field(None, description="Telegram username")
    photo_url: Optional[str] = Field(None, description="Profile photo URL")
    auth_date: int = Field(..., description="Unix timestamp of authentication")
    hash: str = Field(..., description="HMAC-SHA256 hash for verification")


class AuthResponse(BaseModel):
    """Auth response with access token"""

    success: bool
    access_token: Optional[str] = None
    buyer_id: Optional[str] = None
    name: Optional[str] = None
    error: Optional[str] = None


def verify_telegram_auth(data: TelegramAuthData, bot_token: str) -> bool:
    """
    Verify Telegram Login Widget authentication data.

    Algorithm:
    1. Create data_check_string from sorted key=value pairs (excluding hash)
    2. secret_key = SHA256(bot_token)
    3. computed_hash = HMAC-SHA256(data_check_string, secret_key)
    4. Compare computed_hash with provided hash

    Args:
        data: Telegram auth data
        bot_token: Bot token for HMAC key

    Returns:
        True if hash is valid
    """
    # Build data_check_string
    check_dict = {
        "id": data.id,
        "first_name": data.first_name,
        "auth_date": data.auth_date,
    }
    if data.last_name:
        check_dict["last_name"] = data.last_name
    if data.username:
        check_dict["username"] = data.username
    if data.photo_url:
        check_dict["photo_url"] = data.photo_url

    # Sort and join
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(check_dict.items()))

    # Calculate secret key = SHA256(bot_token)
    secret_key = hashlib.sha256(bot_token.encode()).digest()

    # Calculate HMAC-SHA256
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    return hmac.compare_digest(computed_hash, data.hash)


def is_auth_date_valid(auth_date: int) -> bool:
    """Check if auth_date is not older than 24 hours."""
    current_time = int(time.time())
    return (current_time - auth_date) <= AUTH_DATE_MAX_AGE_SECONDS


@router.post(
    "/telegram",
    response_model=AuthResponse,
    summary="Authenticate via Telegram Login Widget",
    description="Verify Telegram Login Widget data and return access token for existing buyers.",
)
async def telegram_auth(data: TelegramAuthData) -> AuthResponse:
    """
    POST /api/auth/telegram

    Authenticate user via Telegram Login Widget.

    Flow:
    1. Verify HMAC-SHA256 hash with bot token
    2. Check auth_date is not older than 24 hours
    3. Find buyer by telegram_id in Supabase
    4. Return access_token if found

    Args:
        data: Telegram Login Widget auth data

    Returns:
        AuthResponse with access_token or error
    """
    from src.core.supabase import get_supabase

    # Get bot token
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        raise HTTPException(status_code=500, detail="TELEGRAM_BOT_TOKEN not configured")

    # Verify hash
    if not verify_telegram_auth(data, bot_token):
        return AuthResponse(success=False, error="Invalid authentication hash")

    # Check auth_date freshness
    if not is_auth_date_valid(data.auth_date):
        return AuthResponse(
            success=False, error="Authentication data expired (older than 24 hours)"
        )

    # Find buyer in Supabase
    sb = get_supabase()
    telegram_id = str(data.id)

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"{sb.rest_url}/buyers",
            headers=sb.get_headers(),
            params={
                "select": "id,name,telegram_id",
                "telegram_id": f"eq.{telegram_id}",
                "limit": "1",
            },
        )

        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Database error: {response.status_code}")

        buyers = response.json()

    if not buyers:
        return AuthResponse(
            success=False, error="Buyer not found. Please register first via Telegram bot."
        )

    buyer = buyers[0]

    # Generate simple access token (buyer_id + timestamp + signature)
    api_key = os.getenv("API_KEY", "")
    token_data = f"{buyer['id']}:{int(time.time())}"
    signature = hmac.new(api_key.encode(), token_data.encode(), hashlib.sha256).hexdigest()[:16]
    access_token = f"{token_data}:{signature}"

    return AuthResponse(
        success=True,
        access_token=access_token,
        buyer_id=buyer["id"],
        name=buyer.get("name") or data.first_name,
    )
