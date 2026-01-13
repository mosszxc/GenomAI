"""
Pydantic Input Models for Supabase Activities

Input validation models for activities in temporal/activities/supabase.py.
Uses Pydantic v2 for automatic validation on construction.

Usage:
    @activity.defn
    async def create_idea(input: CreateIdeaInput) -> Dict[str, Any]:
        # input is already validated
        ...
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator

from temporal.models.validators import (
    validate_uuid,
    validate_sha256_hash,
    validate_url,
    validate_enum,
    CREATIVE_STATUSES,
    SOURCE_TYPES,
)


class CreateCreativeInput(BaseModel):
    """Input for create_creative activity."""

    video_url: str = Field(..., description="Video URL (required)")
    source_type: str = Field(
        ..., description="Source type: telegram, keitaro, historical, spy, user"
    )
    buyer_id: Optional[str] = Field(None, description="Buyer UUID")
    target_geo: Optional[str] = Field(None, description="Target GEO code")
    target_vertical: Optional[str] = Field(None, description="Target vertical")

    @field_validator("video_url")
    @classmethod
    def validate_video_url(cls, v: str) -> str:
        return validate_url(v, "video_url")

    @field_validator("source_type")
    @classmethod
    def validate_source_type(cls, v: str) -> str:
        return validate_enum(v, SOURCE_TYPES, "source_type")

    @field_validator("buyer_id")
    @classmethod
    def validate_buyer_id(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return validate_uuid(v, "buyer_id")
        return v


class CreateHistoricalCreativeInput(BaseModel):
    """Input for create_historical_creative activity."""

    video_url: str = Field(..., description="Video URL (required)")
    tracker_id: str = Field(..., description="Keitaro campaign/tracker ID")
    buyer_id: str = Field(..., description="Buyer UUID (required)")
    metrics: Optional[Dict[str, Any]] = Field(None, description="Keitaro metrics")
    target_geo: Optional[str] = Field(None, description="Target GEO code")
    target_vertical: Optional[str] = Field(None, description="Target vertical")

    @field_validator("video_url")
    @classmethod
    def validate_video_url(cls, v: str) -> str:
        return validate_url(v, "video_url")

    @field_validator("buyer_id")
    @classmethod
    def validate_buyer_id(cls, v: str) -> str:
        return validate_uuid(v, "buyer_id")

    @field_validator("tracker_id")
    @classmethod
    def validate_tracker_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("tracker_id cannot be empty")
        return v.strip()


class GetCreativeInput(BaseModel):
    """Input for get_creative activity."""

    creative_id: str = Field(..., description="Creative UUID")

    @field_validator("creative_id")
    @classmethod
    def validate_creative_id(cls, v: str) -> str:
        return validate_uuid(v, "creative_id")


class GetIdeaInput(BaseModel):
    """Input for get_idea activity."""

    idea_id: str = Field(..., description="Idea UUID")

    @field_validator("idea_id")
    @classmethod
    def validate_idea_id(cls, v: str) -> str:
        return validate_uuid(v, "idea_id")


class CheckIdeaExistsInput(BaseModel):
    """Input for check_idea_exists activity."""

    canonical_hash: str = Field(..., description="SHA256 hash of decomposed creative")

    @field_validator("canonical_hash")
    @classmethod
    def validate_hash(cls, v: str) -> str:
        return validate_sha256_hash(v, "canonical_hash")


class CreateIdeaInput(BaseModel):
    """Input for create_idea activity."""

    canonical_hash: str = Field(..., description="SHA256 hash")
    decomposed_creative_id: str = Field(..., description="Decomposed creative UUID")
    buyer_id: Optional[str] = Field(None, description="Buyer UUID (not stored)")
    avatar_id: Optional[str] = Field(None, description="Avatar UUID")

    @field_validator("canonical_hash")
    @classmethod
    def validate_hash(cls, v: str) -> str:
        return validate_sha256_hash(v, "canonical_hash")

    @field_validator("decomposed_creative_id")
    @classmethod
    def validate_decomposed_id(cls, v: str) -> str:
        return validate_uuid(v, "decomposed_creative_id")

    @field_validator("buyer_id", "avatar_id")
    @classmethod
    def validate_optional_uuids(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return validate_uuid(v, "id")
        return v


class UpsertIdeaInput(BaseModel):
    """Input for upsert_idea activity."""

    canonical_hash: str = Field(..., description="SHA256 hash")
    decomposed_creative_id: str = Field(..., description="Decomposed creative UUID")
    buyer_id: Optional[str] = Field(None, description="Buyer UUID (not stored)")
    avatar_id: Optional[str] = Field(None, description="Avatar UUID")

    @field_validator("canonical_hash")
    @classmethod
    def validate_hash(cls, v: str) -> str:
        return validate_sha256_hash(v, "canonical_hash")

    @field_validator("decomposed_creative_id")
    @classmethod
    def validate_decomposed_id(cls, v: str) -> str:
        return validate_uuid(v, "decomposed_creative_id")

    @field_validator("buyer_id", "avatar_id")
    @classmethod
    def validate_optional_uuids(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return validate_uuid(v, "id")
        return v


class SaveDecomposedCreativeInput(BaseModel):
    """Input for save_decomposed_creative activity."""

    creative_id: str = Field(..., description="Source creative UUID")
    payload: Dict[str, Any] = Field(..., description="LLM decomposition payload")
    canonical_hash: str = Field(..., description="Computed canonical hash")
    transcript_id: Optional[str] = Field(None, description="Transcript UUID")

    @field_validator("creative_id")
    @classmethod
    def validate_creative_id(cls, v: str) -> str:
        return validate_uuid(v, "creative_id")

    @field_validator("canonical_hash")
    @classmethod
    def validate_hash(cls, v: str) -> str:
        return validate_sha256_hash(v, "canonical_hash")

    @field_validator("payload")
    @classmethod
    def validate_payload(cls, v: Any) -> Dict[str, Any]:
        if not isinstance(v, dict):
            raise ValueError(f"payload must be a dict, got {type(v).__name__}: {v!r:.200}")
        return v

    @field_validator("transcript_id")
    @classmethod
    def validate_transcript_id(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return validate_uuid(v, "transcript_id")
        return v


class UpdateCreativeStatusInput(BaseModel):
    """Input for update_creative_status activity."""

    creative_id: str = Field(..., description="Creative UUID")
    status: str = Field(..., description="New status: registered, processing, processed, failed")
    error: Optional[str] = Field(None, description="Error message when status=failed")

    @field_validator("creative_id")
    @classmethod
    def validate_creative_id(cls, v: str) -> str:
        return validate_uuid(v, "creative_id")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        return validate_enum(v, CREATIVE_STATUSES, "status")


class EmitEventInput(BaseModel):
    """Input for emit_event activity."""

    event_type: str = Field(..., description="Event type (e.g., CreativeDecomposed)")
    payload: Dict[str, Any] = Field(..., description="Event payload")
    entity_type: Optional[str] = Field(None, description="Entity type (creative, decision)")
    entity_id: Optional[str] = Field(None, description="Entity UUID")

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("event_type cannot be empty")
        return v.strip()

    @field_validator("entity_id")
    @classmethod
    def validate_entity_id(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return validate_uuid(v, "entity_id")
        return v


class SaveTranscriptInput(BaseModel):
    """Input for save_transcript activity."""

    creative_id: str = Field(..., description="Creative UUID")
    transcript_text: str = Field(..., description="Full transcript text")
    assemblyai_transcript_id: Optional[str] = Field(None, description="AssemblyAI ID")

    @field_validator("creative_id")
    @classmethod
    def validate_creative_id(cls, v: str) -> str:
        return validate_uuid(v, "creative_id")

    @field_validator("transcript_text")
    @classmethod
    def validate_transcript_text(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("transcript_text cannot be empty")
        return v


class GetExistingTranscriptInput(BaseModel):
    """Input for get_existing_transcript activity."""

    creative_id: str = Field(..., description="Creative UUID")

    @field_validator("creative_id")
    @classmethod
    def validate_creative_id(cls, v: str) -> str:
        return validate_uuid(v, "creative_id")
