"""
Schema Validation API routes
"""

import os
from fastapi import APIRouter, Header, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Any

from src.services.schema_validator import get_schema_validator


router = APIRouter()


# Request/Response models
class SchemaValidateRequest(BaseModel):
    """Request model for schema validation"""

    payload: dict = Field(..., description="LLM output to validate")
    schema_version: str = Field(default="v1", description="Schema version (v1, v2)")


class ValidationErrorResponse(BaseModel):
    """Validation error details"""

    field: str
    message: str
    code: str
    value: Optional[Any] = None


class ValidationWarningResponse(BaseModel):
    """Validation warning details"""

    field: str
    message: str


class SchemaValidateResponse(BaseModel):
    """Response model for schema validation"""

    valid: bool
    errors: List[ValidationErrorResponse] = []
    warnings: List[ValidationWarningResponse] = []


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
    "/validate",
    response_model=SchemaValidateResponse,
    summary="Validate LLM output against schema",
    description="Validates a payload against the idea JSON schema. Returns validation errors and warnings.",
)
async def validate_schema(
    request: SchemaValidateRequest, _: bool = Depends(verify_api_key)
) -> SchemaValidateResponse:
    """
    POST /api/schema/validate

    Validate LLM output against JSON schema.

    Args:
        request: Validation request with payload and schema_version

    Returns:
        SchemaValidateResponse: Validation result with errors and warnings
    """
    validator = get_schema_validator()

    result = validator.validate(payload=request.payload, schema_version=request.schema_version)

    return SchemaValidateResponse(
        valid=result.valid,
        errors=[
            ValidationErrorResponse(field=e.field, message=e.message, code=e.code, value=e.value)
            for e in result.errors
        ],
        warnings=[
            ValidationWarningResponse(field=w.field, message=w.message) for w in result.warnings
        ],
    )
