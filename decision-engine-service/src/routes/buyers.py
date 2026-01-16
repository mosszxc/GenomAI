"""
Buyers API Routes

API endpoints for buyer information.
All endpoints require JWT auth (token from /api/auth/telegram).

Routes:
    GET /api/buyers/me - Get current buyer information
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from src.core.supabase import get_supabase
from src.core.http_client import get_http_client
from src.routes.onboarding import verify_jwt_token, TokenPayload

logger = logging.getLogger(__name__)

router = APIRouter()


class BuyerInfoResponse(BaseModel):
    """Response from buyers/me endpoint"""

    success: bool
    id: Optional[str] = None
    telegram_id: Optional[str] = None
    name: Optional[str] = None
    geos: list[str] = []
    verticals: list[str] = []
    keitaro_source: Optional[str] = None
    status: Optional[str] = None
    created_at: Optional[str] = None
    error: Optional[str] = None


@router.get("/me", response_model=BuyerInfoResponse)
async def get_current_buyer(
    token: TokenPayload = Depends(verify_jwt_token),
) -> BuyerInfoResponse:
    """
    Get current buyer information.

    Args:
        token: JWT token payload

    Returns:
        BuyerInfoResponse with buyer details

    Raises:
        HTTPException 404 if buyer not found
    """
    logger.info(f"Getting buyer info for {token.buyer_id}")

    try:
        sb = get_supabase()
    except RuntimeError:
        return BuyerInfoResponse(
            success=False,
            error="Database not configured",
        )

    client = get_http_client()

    try:
        response = await client.get(
            f"{sb.rest_url}/buyers?id=eq.{token.buyer_id}&limit=1",
            headers=sb.get_headers(),
            timeout=10.0,
        )

        if not response.is_success:
            return BuyerInfoResponse(
                success=False,
                error=f"Database error: {response.status_code}",
            )

        buyers = response.json()

        if not buyers:
            raise HTTPException(status_code=404, detail="Buyer not found")

        buyer = buyers[0]

        return BuyerInfoResponse(
            success=True,
            id=buyer.get("id"),
            telegram_id=buyer.get("telegram_id"),
            name=buyer.get("name"),
            geos=buyer.get("geos") or [],
            verticals=buyer.get("verticals") or [],
            keitaro_source=buyer.get("keitaro_source"),
            status=buyer.get("status"),
            created_at=buyer.get("created_at"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get buyer info for {token.buyer_id}: {e}")
        return BuyerInfoResponse(
            success=False,
            error=str(e)[:200],
        )
