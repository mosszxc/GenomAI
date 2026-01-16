"""
Unit tests for onboarding JWT authentication

Issue #746: verify_jwt_token должен поддерживать Supabase JWT токены
"""

import base64
import json
import time
from typing import Optional

import pytest

from src.routes.onboarding import verify_jwt_token, TokenPayload


def create_supabase_jwt(
    sub: str,
    exp: Optional[int] = None,
    user_metadata: Optional[dict] = None,
) -> str:
    """
    Create a mock Supabase JWT token (unsigned).

    Real Supabase JWT structure:
    - Header: {"alg": "HS256", "typ": "JWT"}
    - Payload: {sub, aud, role, exp, user_metadata, ...}
    """
    header = {"alg": "HS256", "typ": "JWT"}

    if exp is None:
        exp = int(time.time()) + 3600  # 1 hour from now

    payload = {
        "sub": sub,
        "aud": "authenticated",
        "role": "authenticated",
        "exp": exp,
        "iat": int(time.time()),
    }

    if user_metadata:
        payload["user_metadata"] = user_metadata

    # Base64 encode (without signature for testing)
    header_b64 = base64.urlsafe_b64encode(
        json.dumps(header).encode()
    ).rstrip(b"=").decode()

    payload_b64 = base64.urlsafe_b64encode(
        json.dumps(payload).encode()
    ).rstrip(b"=").decode()

    # Mock signature
    signature = "mock_signature_for_testing"

    return f"{header_b64}.{payload_b64}.{signature}"


class TestSupabaseJwtAuth:
    """Tests for Supabase JWT token verification"""

    @pytest.mark.asyncio
    async def test_supabase_jwt_should_be_accepted(self):
        """
        Issue #746: Supabase JWT should be accepted

        Cockpit frontend passes Supabase access_token, not custom token.
        verify_jwt_token should decode it and extract buyer_id from 'sub' claim.
        """
        buyer_id = "550e8400-e29b-41d4-a716-446655440000"

        # Create Supabase JWT with buyer_id as sub
        token = create_supabase_jwt(sub=buyer_id)

        # This should NOT raise 401
        result = await verify_jwt_token(f"Bearer {token}")

        assert isinstance(result, TokenPayload)
        assert result.buyer_id == buyer_id

    @pytest.mark.asyncio
    async def test_supabase_jwt_with_telegram_metadata(self):
        """
        Supabase JWT may contain telegram_id in user_metadata
        """
        buyer_id = "550e8400-e29b-41d4-a716-446655440000"
        telegram_id = "123456789"

        token = create_supabase_jwt(
            sub=buyer_id,
            user_metadata={"telegram_id": telegram_id},
        )

        result = await verify_jwt_token(f"Bearer {token}")

        assert result.buyer_id == buyer_id

    @pytest.mark.asyncio
    async def test_expired_supabase_jwt_should_return_401(self):
        """Expired Supabase JWT should return 401"""
        from fastapi import HTTPException

        buyer_id = "550e8400-e29b-41d4-a716-446655440000"
        expired_time = int(time.time()) - 3600  # 1 hour ago

        token = create_supabase_jwt(sub=buyer_id, exp=expired_time)

        with pytest.raises(HTTPException) as exc_info:
            await verify_jwt_token(f"Bearer {token}")

        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()


class TestCustomTokenAuth:
    """Tests for legacy custom token format (buyer_id:timestamp:signature)"""

    @pytest.mark.asyncio
    async def test_custom_token_still_works(self):
        """Legacy custom token format should still work"""
        import hmac
        import hashlib
        import os

        # Set API_KEY for test
        original_key = os.environ.get("API_KEY")
        os.environ["API_KEY"] = "test_api_key_12345"

        try:
            buyer_id = "550e8400-e29b-41d4-a716-446655440000"
            timestamp = int(time.time())
            token_data = f"{buyer_id}:{timestamp}"
            signature = hmac.new(
                "test_api_key_12345".encode(),
                token_data.encode(),
                hashlib.sha256
            ).hexdigest()[:16]

            token = f"{token_data}:{signature}"

            result = await verify_jwt_token(f"Bearer {token}")

            assert result.buyer_id == buyer_id
            assert result.timestamp == timestamp
        finally:
            if original_key:
                os.environ["API_KEY"] = original_key
            else:
                os.environ.pop("API_KEY", None)

    @pytest.mark.asyncio
    async def test_invalid_token_returns_401(self):
        """Invalid token should return 401"""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await verify_jwt_token("Bearer invalid_token_format")

        assert exc_info.value.status_code == 401
