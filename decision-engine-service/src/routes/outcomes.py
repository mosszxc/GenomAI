"""
Outcome Aggregation API routes
"""
import os
from fastapi import APIRouter, Header, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional

from src.services.outcome_service import get_outcome_service


router = APIRouter()


# Request/Response models
class AggregateRequest(BaseModel):
    """Request model for outcome aggregation"""
    snapshot_id: str = Field(..., description="UUID of the daily_metrics_snapshot")


class OutcomeResponse(BaseModel):
    """Outcome aggregate details"""
    id: Optional[str] = None
    creative_id: str
    decision_id: str
    window_id: str
    window_start: Optional[str] = None
    window_end: Optional[str] = None
    conversions: int = 0
    spend: float = 0
    cpa: Optional[float] = None
    origin_type: str = "system"
    learning_applied: bool = False


class ErrorResponse(BaseModel):
    """Error details"""
    code: str
    message: str


class AggregateResponse(BaseModel):
    """Response model for outcome aggregation"""
    success: bool
    outcome: Optional[OutcomeResponse] = None
    learning_triggered: bool = False
    error: Optional[ErrorResponse] = None


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


@router.post(
    "/aggregate",
    response_model=AggregateResponse,
    summary="Aggregate outcome from snapshot",
    description="Aggregates outcome metrics from a daily snapshot and triggers Learning Loop."
)
async def aggregate_outcome(
    request: AggregateRequest,
    _: bool = Depends(verify_api_key)
) -> AggregateResponse:
    """
    POST /api/outcomes/aggregate

    Aggregate outcome from daily metrics snapshot.

    Flow:
    1. Load snapshot data
    2. Find idea via creative_idea_lookup
    3. Find APPROVE decision for idea
    4. Calculate window ID (D1, D3, D7, D7+)
    5. Insert outcome_aggregate
    6. Emit OutcomeAggregated event
    7. Trigger Learning Loop

    Args:
        request: Aggregation request with snapshot_id

    Returns:
        AggregateResponse: Aggregation result with outcome or error
    """
    service = get_outcome_service()

    result = await service.aggregate(snapshot_id=request.snapshot_id)

    if not result.success:
        return AggregateResponse(
            success=False,
            error=ErrorResponse(
                code=result.error_code or "UNKNOWN_ERROR",
                message=result.error_message or "Unknown error occurred"
            )
        )

    # Convert outcome to response
    outcome_data = None
    if result.outcome:
        outcome_data = OutcomeResponse(
            id=result.outcome.id,
            creative_id=result.outcome.creative_id,
            decision_id=result.outcome.decision_id,
            window_id=result.outcome.window_id,
            window_start=str(result.outcome.window_start) if result.outcome.window_start else None,
            window_end=str(result.outcome.window_end) if result.outcome.window_end else None,
            conversions=result.outcome.conversions,
            spend=float(result.outcome.spend) if result.outcome.spend else 0,
            cpa=float(result.outcome.cpa) if result.outcome.cpa else None,
            origin_type=result.outcome.origin_type,
            learning_applied=result.outcome.learning_applied
        )

    return AggregateResponse(
        success=True,
        outcome=outcome_data,
        learning_triggered=result.learning_triggered
    )
