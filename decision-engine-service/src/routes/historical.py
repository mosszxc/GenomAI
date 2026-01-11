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


class StartImportRequest(BaseModel):
    """Request model for start-import endpoint."""

    buyer_id: str = Field(..., description="Buyer UUID")
    keitaro_source: str = Field(..., description="Keitaro source/affiliate parameter")
    date_from: Optional[str] = Field(None, description="Start date (ISO format)")
    date_to: Optional[str] = Field(None, description="End date (ISO format)")


class StartImportResponse(BaseModel):
    """Response model for start-import endpoint."""

    success: bool
    workflow_id: Optional[str] = None
    message: str
    error: Optional[str] = None


@router.post("/start-import", response_model=StartImportResponse)
async def start_import(request: StartImportRequest) -> StartImportResponse:
    """
    Start historical import workflow for a buyer.

    This endpoint triggers the HistoricalImportWorkflow which:
    1. Fetches campaigns from Keitaro by source
    2. Queues them in historical_import_queue
    3. Waits for video URLs to be submitted

    Args:
        request: StartImportRequest with buyer_id and keitaro_source

    Returns:
        StartImportResponse with workflow_id and status
    """
    from temporal.workflows.historical_import import HistoricalImportWorkflow
    from temporal.models.buyer import HistoricalImportInput

    try:
        client = await get_temporal_client()

        workflow_id = f"historical-import-{request.buyer_id}"

        await client.start_workflow(
            HistoricalImportWorkflow.run,
            HistoricalImportInput(
                buyer_id=request.buyer_id,
                keitaro_source=request.keitaro_source,
                date_from=request.date_from,
                date_to=request.date_to,
            ),
            id=workflow_id,
            task_queue="telegram",
        )

        logger.info(
            f"Started historical import: {workflow_id} "
            f"for buyer {request.buyer_id}, source {request.keitaro_source}"
        )

        return StartImportResponse(
            success=True,
            workflow_id=workflow_id,
            message=f"Historical import started for source '{request.keitaro_source}'",
        )

    except Exception as e:
        logger.error(f"Failed to start historical import: {e}")
        return StartImportResponse(
            success=False,
            message="Failed to start historical import",
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
                f"&status=in.(pending_video,ready,processing)"
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
