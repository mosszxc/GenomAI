"""
Learning Loop API routes
"""

from fastapi import APIRouter, Header, HTTPException, Depends
from typing import Optional
from src.services.learning_loop import (
    process_learning_batch,
    fetch_unprocessed_outcomes,
)
from src.utils.errors import SupabaseError

router = APIRouter()


async def verify_api_key(authorization: Optional[str] = Header(None)):
    """
    Verify API Key from Authorization header
    """
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


@router.post("/process")
async def process_learning(_: bool = Depends(verify_api_key)):
    """
    POST /learning/process

    Process all unprocessed outcomes and apply learning.

    This endpoint is designed to be called by n8n cron job every 15 minutes.

    Flow:
    1. Fetch unprocessed outcomes (learning_applied=false, origin_type=system)
    2. For each outcome:
       - Resolve idea via decomposed_creatives
       - Calculate confidence delta with time_decay + environment_weight
       - Insert new confidence version
       - Check death conditions
       - Mark outcome as processed
    3. Return summary

    Returns:
        dict: Learning processing result
            - processed_count: Number of outcomes processed
            - updated_ideas: List of updated idea IDs
            - new_deaths: List of ideas that died
            - errors: List of any errors encountered
    """
    try:
        result = await process_learning_batch(limit=100)

        return {"success": True, "data": result.to_dict()}

    except SupabaseError as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": {"code": "SUPABASE_ERROR", "message": str(e)},
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": {"code": "INTERNAL_ERROR", "message": str(e)},
            },
        )


@router.get("/status")
async def learning_status(_: bool = Depends(verify_api_key)):
    """
    GET /learning/status

    Get count of pending outcomes to process.

    Returns:
        dict: Status info
            - pending_outcomes: Number of outcomes waiting for processing
    """
    try:
        outcomes = await fetch_unprocessed_outcomes(limit=1000)

        return {"success": True, "data": {"pending_outcomes": len(outcomes)}}

    except SupabaseError as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": {"code": "SUPABASE_ERROR", "message": str(e)},
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": {"code": "INTERNAL_ERROR", "message": str(e)},
            },
        )
