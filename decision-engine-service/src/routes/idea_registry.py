"""
Idea Registry API routes

POST /api/idea-registry/register - Register idea for a creative
"""

from fastapi import APIRouter, Header, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from src.services.idea_registry import (
    register_idea,
    IdeaRegistryError,
    DecomposedCreativeNotFoundError,
)

router = APIRouter()


class RegisterRequest(BaseModel):
    """Request body for register endpoint"""

    creative_id: str
    schema_version: str = "v1"


class RegisterResponseData(BaseModel):
    """Data portion of response"""

    idea_id: str
    status: str
    canonical_hash: str
    avatar_id: Optional[str] = None
    avatar_status: Optional[str] = None


class RegisterResponse(BaseModel):
    """Response model for register endpoint"""

    success: bool
    data: RegisterResponseData


async def verify_api_key(authorization: Optional[str] = Header(None)):
    """
    Verify API Key from Authorization header.

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


@router.post("/register", response_model=RegisterResponse)
async def register(request: RegisterRequest, _: bool = Depends(verify_api_key)):
    """
    POST /api/idea-registry/register

    Register idea for a creative.

    Flow:
    1. Load decomposed_creative by creative_id
    2. Load buyer linked to creative
    3. Compute canonical_hash from payload
    4. Find or create idea
    5. Find or create avatar
    6. Link idea to decomposed_creative
    7. Emit IdeaRegistered event
    8. Return result

    Request Body:
        - creative_id (required): UUID of the creative
        - schema_version (optional): Schema version (default: v1)

    Returns:
        RegisterResponse with success=True and data containing:
        - idea_id: UUID of the idea
        - status: 'new' or 'reused'
        - canonical_hash: SHA256 hash
        - avatar_id: UUID of avatar (if any)
        - avatar_status: 'new', 'existing', or null

    Errors:
        - 404: Decomposed creative not found
        - 401: Invalid API key
        - 500: Internal error
    """
    try:
        result = await register_idea(
            creative_id=request.creative_id, schema_version=request.schema_version
        )

        return RegisterResponse(
            success=True,
            data=RegisterResponseData(
                idea_id=result.idea_id,
                status=result.status,
                canonical_hash=result.canonical_hash,
                avatar_id=result.avatar_id,
                avatar_status=result.avatar_status,
            ),
        )

    except DecomposedCreativeNotFoundError as e:
        raise HTTPException(status_code=404, detail={"success": False, "error": str(e)}) from e

    except IdeaRegistryError as e:
        raise HTTPException(status_code=500, detail={"success": False, "error": str(e)}) from e

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"success": False, "error": f"Internal error: {str(e)}"},
        ) from e
