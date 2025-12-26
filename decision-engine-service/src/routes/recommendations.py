"""
Recommendations API routes

Issue: #124
"""
from fastapi import APIRouter, Header, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from src.services.recommendation import (
    generate_recommendation,
    mark_recommendation_executed,
    record_recommendation_outcome,
    get_recommendation,
    get_pending_recommendations,
    get_recommendation_stats
)
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


class GenerateRequest(BaseModel):
    buyer_id: Optional[str] = None
    avatar_id: Optional[str] = None
    geo: Optional[str] = None
    vertical: Optional[str] = None
    force_exploration: bool = False


class ExecutedRequest(BaseModel):
    creative_id: str


class OutcomeRequest(BaseModel):
    was_successful: bool
    cpa: Optional[float] = None
    spend: Optional[float] = None
    revenue: Optional[float] = None


# Static routes MUST come before dynamic routes with path parameters

@router.post("/generate")
async def generate(
    request: GenerateRequest,
    _: bool = Depends(verify_api_key)
):
    """
    POST /recommendations/generate

    Generate a recommendation for buyer.

    75% exploitation (proven components), 25% exploration (Thompson Sampling).

    Request body:
        - buyer_id: Optional buyer ID
        - avatar_id: Optional target avatar
        - geo: Geographic context
        - vertical: Vertical context
        - force_exploration: Force exploration mode (default: false)

    Returns:
        - id: Recommendation ID
        - mode: exploitation | exploration
        - description: Human-readable recommendation
        - components: List of recommended components with confidence
    """
    try:
        rec = await generate_recommendation(
            buyer_id=request.buyer_id,
            avatar_id=request.avatar_id,
            geo=request.geo,
            vertical=request.vertical,
            force_exploration=request.force_exploration
        )

        return {
            "success": True,
            "data": {
                "id": rec.id,
                "mode": rec.mode,
                "exploration_type": rec.exploration_type,
                "description": rec.description,
                "avg_confidence": rec.avg_confidence,
                "components": [
                    {
                        "type": c.component_type,
                        "value": c.component_value,
                        "confidence": c.confidence,
                        "sample_size": c.sample_size,
                        "is_exploration": c.is_exploration
                    }
                    for c in rec.components
                ]
            }
        }

    except SupabaseError as e:
        raise HTTPException(
            status_code=500,
            detail={"success": False, "error": {"code": "SUPABASE_ERROR", "message": str(e)}}
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"success": False, "error": {"code": "INTERNAL_ERROR", "message": str(e)}}
        )


@router.get("/stats")
async def stats(
    _: bool = Depends(verify_api_key)
):
    """
    GET /recommendations/stats

    Get recommendation statistics for monitoring.
    """
    try:
        result = await get_recommendation_stats()

        return {
            "success": True,
            "data": result
        }

    except SupabaseError as e:
        raise HTTPException(
            status_code=500,
            detail={"success": False, "error": {"code": "SUPABASE_ERROR", "message": str(e)}}
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"success": False, "error": {"code": "INTERNAL_ERROR", "message": str(e)}}
        )


@router.get("/")
async def list_pending(
    buyer_id: Optional[str] = None,
    _: bool = Depends(verify_api_key)
):
    """
    GET /recommendations/

    Get pending recommendations, optionally filtered by buyer.

    Query params:
        - buyer_id: Filter by buyer (optional)
    """
    try:
        recs = await get_pending_recommendations(buyer_id)

        return {
            "success": True,
            "data": recs
        }

    except SupabaseError as e:
        raise HTTPException(
            status_code=500,
            detail={"success": False, "error": {"code": "SUPABASE_ERROR", "message": str(e)}}
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"success": False, "error": {"code": "INTERNAL_ERROR", "message": str(e)}}
        )


# Dynamic routes with path parameters come after static routes

@router.post("/{recommendation_id}/executed")
async def mark_executed(
    recommendation_id: str,
    request: ExecutedRequest,
    _: bool = Depends(verify_api_key)
):
    """
    POST /recommendations/{id}/executed

    Mark recommendation as executed when buyer creates creative.

    Request body:
        - creative_id: ID of created creative
    """
    try:
        result = await mark_recommendation_executed(
            recommendation_id=recommendation_id,
            creative_id=request.creative_id
        )

        return {
            "success": True,
            "data": result
        }

    except SupabaseError as e:
        raise HTTPException(
            status_code=500,
            detail={"success": False, "error": {"code": "SUPABASE_ERROR", "message": str(e)}}
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"success": False, "error": {"code": "INTERNAL_ERROR", "message": str(e)}}
        )


@router.post("/{recommendation_id}/outcome")
async def record_outcome(
    recommendation_id: str,
    request: OutcomeRequest,
    _: bool = Depends(verify_api_key)
):
    """
    POST /recommendations/{id}/outcome

    Record outcome for a recommendation after learning.

    Request body:
        - was_successful: Whether recommendation led to good outcome
        - cpa: Cost per acquisition (optional)
        - spend: Total spend (optional)
        - revenue: Total revenue (optional)
    """
    try:
        result = await record_recommendation_outcome(
            recommendation_id=recommendation_id,
            was_successful=request.was_successful,
            cpa=request.cpa,
            spend=request.spend,
            revenue=request.revenue
        )

        return {
            "success": True,
            "data": result
        }

    except SupabaseError as e:
        raise HTTPException(
            status_code=500,
            detail={"success": False, "error": {"code": "SUPABASE_ERROR", "message": str(e)}}
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"success": False, "error": {"code": "INTERNAL_ERROR", "message": str(e)}}
        )


@router.get("/{recommendation_id}")
async def get_one(
    recommendation_id: str,
    _: bool = Depends(verify_api_key)
):
    """
    GET /recommendations/{id}

    Get recommendation by ID.
    """
    try:
        rec = await get_recommendation(recommendation_id)

        if not rec:
            raise HTTPException(status_code=404, detail="Recommendation not found")

        return {
            "success": True,
            "data": rec
        }

    except HTTPException:
        raise
    except SupabaseError as e:
        raise HTTPException(
            status_code=500,
            detail={"success": False, "error": {"code": "SUPABASE_ERROR", "message": str(e)}}
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"success": False, "error": {"code": "INTERNAL_ERROR", "message": str(e)}}
        )
