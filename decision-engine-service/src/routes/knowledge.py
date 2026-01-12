"""
Knowledge Extraction API routes

Issue: #300
"""

import os
import httpx
from fastapi import APIRouter, Header, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Literal

router = APIRouter()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")


async def verify_api_key(authorization: Optional[str] = Header(None)):
    """Verify API Key from Authorization header"""
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


def get_headers():
    """Get Supabase REST API headers for genomai schema."""
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
        "Accept-Profile": "genomai",
        "Content-Profile": "genomai",
    }


# Request/Response models


class UploadSourceRequest(BaseModel):
    title: str
    content: str
    source_type: Literal["youtube", "file", "manual", "transcript"] = "file"
    url: Optional[str] = None
    created_by: Optional[str] = None


class UploadSourceResponse(BaseModel):
    source_id: Optional[str] = None
    workflow_id: str
    status: str


class ExtractionResponse(BaseModel):
    id: str
    source_id: str
    knowledge_type: str
    name: str
    description: Optional[str]
    payload: dict
    confidence_score: Optional[float]
    supporting_quotes: Optional[List[str]]
    status: str
    created_at: str


class ApproveRequest(BaseModel):
    reviewed_by: Optional[str] = None


class RejectRequest(BaseModel):
    reviewed_by: Optional[str] = None
    reason: Optional[str] = None


# Routes


@router.post("/sources", response_model=UploadSourceResponse)
async def upload_source(
    request: UploadSourceRequest, _: bool = Depends(verify_api_key)
):
    """
    POST /api/knowledge/sources

    Upload transcript for knowledge extraction.

    Request body:
        - title: Source title/name
        - content: Full transcript text
        - source_type: 'youtube', 'file', or 'manual'
        - url: Optional source URL
        - created_by: Optional admin telegram_id

    Returns:
        - workflow_id: Temporal workflow ID
        - status: 'processing'

    Starts KnowledgeIngestionWorkflow to:
        1. Save source
        2. Extract knowledge via LLM
        3. Save pending extractions
        4. Notify admin
    """
    from temporal.models.knowledge import KnowledgeSourceInput
    from temporal.client import get_temporal_client

    try:
        client = await get_temporal_client()

        input_data = KnowledgeSourceInput(
            title=request.title,
            content=request.content,
            source_type=request.source_type,
            url=request.url,
            created_by=request.created_by,
        )

        handle = await client.start_workflow(
            "KnowledgeIngestionWorkflow",
            input_data,
            id=f"knowledge-ingest-{request.title[:20].replace(' ', '-')}",
            task_queue="knowledge",
        )

        return UploadSourceResponse(
            workflow_id=handle.id,
            status="processing",
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to start workflow: {str(e)}"
        )


@router.get("/extractions")
async def list_extractions(
    status: Optional[str] = "pending",
    knowledge_type: Optional[str] = None,
    limit: int = 20,
    _: bool = Depends(verify_api_key),
):
    """
    GET /api/knowledge/extractions

    List knowledge extractions by status.

    Query params:
        - status: 'pending', 'approved', 'rejected', 'applied' (default: pending)
        - knowledge_type: Filter by type
        - limit: Max results (default 20)

    Returns list of extractions.
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise HTTPException(status_code=500, detail="Supabase not configured")

    try:
        url = (
            f"{SUPABASE_URL}/rest/v1/knowledge_extractions"
            f"?status=eq.{status}&order=created_at.desc&limit={limit}"
        )

        if knowledge_type:
            url += f"&knowledge_type=eq.{knowledge_type}"

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=get_headers())

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Supabase error: {response.text}",
                )

            extractions = response.json()
            return {
                "extractions": extractions,
                "count": len(extractions),
                "status_filter": status,
            }

    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Request failed: {str(e)}")


@router.get("/extractions/{extraction_id}")
async def get_extraction(extraction_id: str, _: bool = Depends(verify_api_key)):
    """
    GET /api/knowledge/extractions/{id}

    Get single extraction by ID.
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise HTTPException(status_code=500, detail="Supabase not configured")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{SUPABASE_URL}/rest/v1/knowledge_extractions?id=eq.{extraction_id}",
                headers=get_headers(),
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Supabase error: {response.text}",
                )

            results = response.json()
            if not results:
                raise HTTPException(status_code=404, detail="Extraction not found")

            return results[0]

    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Request failed: {str(e)}")


@router.post("/extractions/{extraction_id}/approve")
async def approve_extraction(
    extraction_id: str,
    request: ApproveRequest,
    _: bool = Depends(verify_api_key),
):
    """
    POST /api/knowledge/extractions/{id}/approve

    Approve extraction and apply to system.

    Starts KnowledgeApplicationWorkflow to apply the knowledge.
    """
    from temporal.models.knowledge import ApplyKnowledgeInput
    from temporal.client import get_temporal_client

    try:
        client = await get_temporal_client()

        input_data = ApplyKnowledgeInput(
            extraction_id=extraction_id,
            reviewed_by=request.reviewed_by,
        )

        handle = await client.start_workflow(
            "KnowledgeApplicationWorkflow",
            input_data,
            id=f"knowledge-apply-{extraction_id[:8]}",
            task_queue="knowledge",
        )

        return {
            "extraction_id": extraction_id,
            "workflow_id": handle.id,
            "status": "applying",
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to start workflow: {str(e)}"
        )


@router.post("/extractions/{extraction_id}/reject")
async def reject_extraction(
    extraction_id: str,
    request: RejectRequest,
    _: bool = Depends(verify_api_key),
):
    """
    POST /api/knowledge/extractions/{id}/reject

    Reject extraction with optional reason.
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise HTTPException(status_code=500, detail="Supabase not configured")

    from datetime import datetime

    try:
        update_data = {
            "status": "rejected",
            "reviewed_at": datetime.utcnow().isoformat(),
        }

        if request.reviewed_by:
            update_data["reviewed_by"] = request.reviewed_by

        if request.reason:
            update_data["review_notes"] = request.reason

        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{SUPABASE_URL}/rest/v1/knowledge_extractions?id=eq.{extraction_id}",
                headers=get_headers(),
                json=update_data,
            )

            if response.status_code not in (200, 204):
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Supabase error: {response.text}",
                )

            return {
                "extraction_id": extraction_id,
                "status": "rejected",
            }

    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Request failed: {str(e)}")


@router.get("/sources/{source_id}")
async def get_source(source_id: str, _: bool = Depends(verify_api_key)):
    """
    GET /api/knowledge/sources/{id}

    Get source with its extractions.
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise HTTPException(status_code=500, detail="Supabase not configured")

    try:
        async with httpx.AsyncClient() as client:
            # Get source
            source_response = await client.get(
                f"{SUPABASE_URL}/rest/v1/knowledge_sources?id=eq.{source_id}",
                headers=get_headers(),
            )

            if source_response.status_code != 200:
                raise HTTPException(
                    status_code=source_response.status_code,
                    detail=f"Supabase error: {source_response.text}",
                )

            sources = source_response.json()
            if not sources:
                raise HTTPException(status_code=404, detail="Source not found")

            source = sources[0]

            # Get extractions for this source
            extractions_response = await client.get(
                f"{SUPABASE_URL}/rest/v1/knowledge_extractions"
                f"?source_id=eq.{source_id}&order=created_at.asc",
                headers=get_headers(),
            )

            extractions = (
                extractions_response.json()
                if extractions_response.status_code == 200
                else []
            )

            return {
                "source": source,
                "extractions": extractions,
                "extraction_count": len(extractions),
            }

    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Request failed: {str(e)}")
