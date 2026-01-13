"""
Premise API routes

Issue: #169
"""

import os
from src.core.http_client import get_http_client
from src.core.supabase import get_supabase
from fastapi import APIRouter, Header, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from dataclasses import asdict

from src.services.premise_selector import (
    select_premise_for_hypothesis,
    get_top_premises,
    get_active_premises,
)
from src.utils.errors import SupabaseError


router = APIRouter()


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


# Request/Response models


class SelectRequest(BaseModel):
    idea_id: str
    avatar_id: Optional[str] = None
    geo: Optional[str] = None
    vertical: Optional[str] = None
    force_exploration: bool = False


class SelectResponse(BaseModel):
    premise_id: Optional[str]
    premise_type: str
    name: str
    origin_story: Optional[str]
    mechanism_claim: Optional[str]
    is_new: bool
    selection_reason: str


class CreatePremiseRequest(BaseModel):
    premise_type: str
    name: str
    description: Optional[str] = None
    origin_story: Optional[str] = None
    mechanism_claim: Optional[str] = None
    source: str = "manual"
    vertical: Optional[str] = None
    geo: Optional[str] = None


class PremiseResponse(BaseModel):
    id: str
    premise_type: str
    name: str
    description: Optional[str]
    origin_story: Optional[str]
    mechanism_claim: Optional[str]
    source: Optional[str]
    status: str
    vertical: Optional[str]
    geo: Optional[str]


class TopPremiseResponse(BaseModel):
    premise_id: str
    premise_type: str
    win_rate: float
    sample_size: int


# Routes


@router.post("/select", response_model=SelectResponse)
async def select_premise(request: SelectRequest, _: bool = Depends(verify_api_key)):
    """
    POST /premise/select

    Select premise for hypothesis generation.

    75% exploitation (best win_rate), 25% exploration (undersampled or new).

    Request body:
        - idea_id: ID of the idea for hypothesis generation
        - avatar_id: Optional target avatar
        - geo: Geographic context
        - vertical: Vertical filter
        - force_exploration: Force exploration mode

    Returns:
        - premise_id: Selected premise ID (null if is_new=true)
        - premise_type: Type of premise
        - name: Premise name
        - origin_story: Origin narrative
        - mechanism_claim: What it claims to do
        - is_new: True if LLM should generate new premise
        - selection_reason: exploitation | exploration | generation
    """
    try:
        result = await select_premise_for_hypothesis(
            idea_id=request.idea_id,
            avatar_id=request.avatar_id,
            geo=request.geo,
            vertical=request.vertical,
            force_exploration=request.force_exploration,
        )

        return SelectResponse(**asdict(result))

    except SupabaseError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Selection failed: {str(e)}") from e


@router.get("/top")
async def get_top(
    vertical: Optional[str] = None,
    geo: Optional[str] = None,
    avatar_id: Optional[str] = None,
    limit: int = 10,
    _: bool = Depends(verify_api_key),
):
    """
    GET /premise/top

    Get top performing premises by win_rate.

    Query params:
        - vertical: Filter by vertical
        - geo: Filter by geo
        - avatar_id: Filter by avatar
        - limit: Max results (default 10)

    Returns list of premises with win_rate stats.
    """
    try:
        results = await get_top_premises(
            vertical=vertical, geo=geo, avatar_id=avatar_id, limit=limit
        )
        return {"premises": results, "count": len(results)}

    except SupabaseError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}") from e


@router.get("/active")
async def get_active(
    vertical: Optional[str] = None,
    geo: Optional[str] = None,
    limit: int = 50,
    _: bool = Depends(verify_api_key),
):
    """
    GET /premise/active

    Get all active premises.

    Query params:
        - vertical: Filter by vertical
        - geo: Filter by geo
        - limit: Max results (default 50)

    Returns list of active premises.
    """
    try:
        results = await get_active_premises(vertical=vertical, geo=geo, limit=limit)
        return {"premises": results, "count": len(results)}

    except SupabaseError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}") from e


@router.post("/", response_model=PremiseResponse)
async def create_premise(
    request: CreatePremiseRequest, _: bool = Depends(verify_api_key)
):
    """
    POST /premise/

    Create a new premise manually.

    Request body:
        - premise_type: method, discovery, confession, secret, ingredient, mechanism, breakthrough, transformation
        - name: Human-readable name
        - description: Optional description
        - origin_story: How it was discovered
        - mechanism_claim: What it claims to do
        - source: manual (default), llm_generated, extracted
        - vertical: Optional vertical constraint
        - geo: Optional geo constraint

    Returns created premise.
    """
    # Validate premise_type
    valid_types = [
        "method",
        "discovery",
        "confession",
        "secret",
        "ingredient",
        "mechanism",
        "breakthrough",
        "transformation",
    ]
    if request.premise_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid premise_type. Must be one of: {', '.join(valid_types)}",
        )

    # Validate source
    valid_sources = ["manual", "llm_generated", "extracted"]
    if request.source not in valid_sources:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid source. Must be one of: {', '.join(valid_sources)}",
        )

    try:
        sb = get_supabase()
    except RuntimeError:
        raise HTTPException(status_code=500, detail="Missing Supabase credentials") from None

    try:
        headers = sb.get_headers(for_write=True)

        client = get_http_client()
        response = await client.post(
            f"{sb.rest_url}/premises",
            headers=headers,
            json={
                "premise_type": request.premise_type,
                "name": request.name,
                "description": request.description,
                "origin_story": request.origin_story,
                "mechanism_claim": request.mechanism_claim,
                "source": request.source,
                "vertical": request.vertical,
                "geo": request.geo,
                "status": "emerging",
            },
        )

        if response.status_code == 409:
            raise HTTPException(
                status_code=409,
                detail=f"Premise with name '{request.name}' already exists for this vertical",
            )

        response.raise_for_status()
        data = response.json()

        if data:
            return PremiseResponse(**data[0])
        raise HTTPException(status_code=500, detail="Failed to create premise")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Create failed: {str(e)}") from e


@router.get("/{premise_id}")
async def get_premise(premise_id: str, _: bool = Depends(verify_api_key)):
    """
    GET /premise/{premise_id}

    Get premise by ID.
    """
    try:
        sb = get_supabase()
    except RuntimeError:
        raise HTTPException(status_code=500, detail="Missing Supabase credentials") from None

    try:
        headers = sb.get_headers()

        client = get_http_client()
        response = await client.get(
            f"{sb.rest_url}/premises?id=eq.{premise_id}", headers=headers
        )
        response.raise_for_status()
        data = response.json()

        if not data:
            raise HTTPException(status_code=404, detail="Premise not found")

        return data[0]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}") from e
