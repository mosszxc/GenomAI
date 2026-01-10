"""
Decision API routes
"""

from fastapi import APIRouter, Header, HTTPException, Depends
from typing import Optional
from src.services.decision_engine import make_decision
from src.utils.validators import validate_decision_request
from src.utils.errors import InvalidInputError, DecisionEngineError

router = APIRouter()


async def verify_api_key(authorization: Optional[str] = Header(None)):
    """
    Verify API Key from Authorization header

    Args:
        authorization: Authorization header value

    Returns:
        bool: True if valid

    Raises:
        HTTPException: If API key is invalid
    """
    import os

    api_key = os.getenv("API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="API_KEY not configured")

    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    # Extract Bearer token
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization format")

    token = authorization.replace("Bearer ", "")

    if token != api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return True


@router.post("/")
async def create_decision(body: dict, _: bool = Depends(verify_api_key)):
    """
    POST /api/decision

    Make decision for an idea

    Optimized: Only idea_id is required. Render API will load all necessary data from Supabase.

    Request Body (optimized):
        - idea_id (required): UUID of idea
        - idea (optional): Idea object (for backward compatibility, not recommended)
        - system_state (optional): System state (for backward compatibility, not recommended)
        - fatigue_state (optional): Fatigue state (for backward compatibility, not recommended)
        - death_memory (optional): Death memory (for backward compatibility, not recommended)

    Returns:
        dict: Decision result with decision and decision_trace

    Note: For optimal performance, pass only idea_id. Render API will load idea,
    system_state, fatigue_state, and death_memory from Supabase automatically.
    """
    # Validate request
    validation_error = validate_decision_request(body)
    if validation_error:
        raise InvalidInputError(validation_error)

    try:
        # Make decision
        result = await make_decision(body)

        # Return success response
        return {"success": True, **result}
    except DecisionEngineError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail={
                "success": False,
                "error": {"code": e.code, "message": e.message, "details": e.details},
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": {"code": "INTERNAL_ERROR", "message": str(e), "details": {}},
            },
        )
