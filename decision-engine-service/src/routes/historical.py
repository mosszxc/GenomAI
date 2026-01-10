"""
Historical Import Routes

API endpoints for historical import operations.

Routes:
    POST /api/historical/submit-video - Submit video URL for historical import
"""

import logging
from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()


class SubmitVideoRequest(BaseModel):
    """Request model for submit-video endpoint."""

    campaign_id: str = Field(..., description="Keitaro campaign ID from import queue")
    video_url: str = Field(..., description="Video URL to process")
    buyer_id: str = Field(..., description="Buyer UUID")


class SubmitVideoResponse(BaseModel):
    """Response model for submit-video endpoint."""

    success: bool
    workflow_id: Optional[str] = None
    message: str
    error: Optional[str] = None


async def get_temporal_client():
    """Get Temporal client."""
    from temporal.client import get_temporal_client as get_client

    return await get_client()


@router.post("/submit-video", response_model=SubmitVideoResponse)
async def submit_video(request: SubmitVideoRequest) -> SubmitVideoResponse:
    """
    Submit video URL for historical import.

    This endpoint triggers the HistoricalVideoHandlerWorkflow which:
    1. Finds the queue record by campaign_id
    2. Updates the queue with video_url
    3. Creates a creative with source_type='historical'
    4. Starts the CreativePipelineWorkflow
    5. Updates queue status to completed

    Args:
        request: SubmitVideoRequest with campaign_id, video_url, buyer_id

    Returns:
        SubmitVideoResponse with workflow_id and status
    """
    from temporal.workflows.historical_import import HistoricalVideoHandlerWorkflow
    from temporal.models.buyer import HistoricalVideoHandlerInput

    try:
        client = await get_temporal_client()

        # Workflow ID is unique per campaign
        workflow_id = f"historical-video-{request.campaign_id}"

        await client.start_workflow(
            HistoricalVideoHandlerWorkflow.run,
            HistoricalVideoHandlerInput(
                campaign_id=request.campaign_id,
                video_url=request.video_url,
                buyer_id=request.buyer_id,
            ),
            id=workflow_id,
            task_queue="telegram",
        )

        logger.info(
            f"Started historical video handler: {workflow_id} "
            f"for campaign {request.campaign_id}"
        )

        return SubmitVideoResponse(
            success=True,
            workflow_id=workflow_id,
            message=f"Video processing started for campaign {request.campaign_id}",
        )

    except Exception as e:
        logger.error(f"Failed to start historical video handler: {e}")
        return SubmitVideoResponse(
            success=False,
            message="Failed to start video processing",
            error=str(e),
        )


@router.get("/queue/{buyer_id}")
async def get_pending_imports(buyer_id: str):
    """
    Get pending historical imports for a buyer.

    Args:
        buyer_id: Buyer UUID

    Returns:
        List of pending import records
    """
    import httpx
    import os

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        return {"success": False, "error": "Supabase not configured"}

    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Accept-Profile": "genomai",
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{supabase_url}/rest/v1/historical_import_queue"
                f"?buyer_id=eq.{buyer_id}"
                f"&status=in.(pending,pending_video,ready)"
                f"&order=created_at.asc"
                f"&limit=50",
                headers=headers,
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

            return {
                "success": True,
                "count": len(data),
                "imports": data,
            }

    except Exception as e:
        logger.error(f"Failed to get pending imports: {e}")
        return {"success": False, "error": str(e)}
