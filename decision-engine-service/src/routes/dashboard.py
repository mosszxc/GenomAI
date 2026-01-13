"""
Dashboard API routes

Provides HOT/COLD/GAPS meta analysis for creative components.

Issue: #602
"""

from fastapi import APIRouter, Header, HTTPException, Depends
from typing import Optional

from src.services.dashboard_service import get_dashboard_meta
from src.utils.errors import SupabaseError

router = APIRouter()


async def verify_api_key(authorization: Optional[str] = Header(None)):
    """Verify API Key from Authorization header"""
    import os

    api_key = os.getenv("API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="API_KEY not configured")

    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization format")

    token = authorization.replace("Bearer ", "")

    if token != api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return True


@router.get("/meta")
async def get_meta(
    geo: Optional[str] = None,
    vertical: Optional[str] = None,
    _: bool = Depends(verify_api_key),
):
    """
    GET /api/dashboard/meta

    Get dashboard meta analysis for HOT/COLD/GAPS components.

    Query params:
        - geo: Filter by geographic region (optional)
        - vertical: Filter by vertical (optional)

    Returns:
        - geo: Requested geo filter
        - vertical: Requested vertical filter
        - week: Current ISO week number
        - hot: Top performing components (high win_rate, sufficient samples)
        - cold: Underperforming components (low win_rate, declining trend)
        - gaps: Underexplored components (low sample_size, need more data)
        - summary: Counts of each category
    """
    try:
        result = await get_dashboard_meta(geo=geo, vertical=vertical)
        return {"success": True, "data": result}

    except SupabaseError as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": {"code": "SUPABASE_ERROR", "message": str(e)},
            },
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": {"code": "INTERNAL_ERROR", "message": str(e)},
            },
        ) from e
