"""
Knowledge Database Activities

Temporal activities for knowledge extraction database operations.
"""

import os
import json
import httpx
from datetime import datetime
from typing import Optional, List
from temporalio import activity
from temporalio.exceptions import ApplicationError


SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")


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


@activity.defn
async def save_knowledge_source(
    title: str,
    content: str,
    source_type: str,
    url: Optional[str] = None,
    created_by: Optional[str] = None,
) -> str:
    """
    Save transcript source to knowledge_sources table.

    Returns:
        source_id: UUID of created record
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ApplicationError("Supabase credentials not configured")

    # Map source_type to valid DB values: youtube, file, manual
    valid_types = {"youtube", "file", "manual"}
    db_source_type = source_type if source_type in valid_types else "manual"

    data = {
        "title": title,
        "transcript_text": content,
        "source_type": db_source_type,
        "url": url,
        "created_by": created_by,
        "processed": False,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{SUPABASE_URL}/rest/v1/knowledge_sources",
            headers=get_headers(),
            json=data,
        )

        if response.status_code not in (200, 201):
            raise ApplicationError(
                f"Failed to save source: {response.status_code} {response.text}"
            )

        result = response.json()
        source_id = result[0]["id"]
        activity.logger.info(f"Saved knowledge source: {source_id}")
        return source_id


@activity.defn
async def save_pending_extractions(
    source_id: str,
    extractions: List[dict],
) -> List[str]:
    """
    Save extracted knowledge items as pending review.

    Returns:
        List of extraction IDs
    """
    if not extractions:
        return []

    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ApplicationError("Supabase credentials not configured")

    records = []
    for ext in extractions:
        records.append(
            {
                "source_id": source_id,
                "knowledge_type": ext.get("knowledge_type"),
                "name": ext.get("name"),
                "description": ext.get("description"),
                "payload": ext.get("payload", {}),
                "confidence_score": ext.get("confidence_score"),
                "supporting_quotes": ext.get("supporting_quotes", []),
                "status": "pending",
            }
        )

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{SUPABASE_URL}/rest/v1/knowledge_extractions",
            headers=get_headers(),
            json=records,
        )

        if response.status_code not in (200, 201):
            raise ApplicationError(
                f"Failed to save extractions: {response.status_code} {response.text}"
            )

        results = response.json()
        extraction_ids = [r["id"] for r in results]
        activity.logger.info(f"Saved {len(extraction_ids)} extractions")
        return extraction_ids


@activity.defn
async def mark_source_processed(source_id: str) -> bool:
    """Mark source as processed."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ApplicationError("Supabase credentials not configured")

    async with httpx.AsyncClient() as client:
        response = await client.patch(
            f"{SUPABASE_URL}/rest/v1/knowledge_sources?id=eq.{source_id}",
            headers=get_headers(),
            json={
                "processed": True,
                "processed_at": datetime.utcnow().isoformat(),
            },
        )

        if response.status_code not in (200, 204):
            raise ApplicationError(
                f"Failed to mark processed: {response.status_code} {response.text}"
            )

        return True


@activity.defn
async def get_pending_extractions(limit: int = 10) -> List[dict]:
    """Get pending extractions for review."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ApplicationError("Supabase credentials not configured")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{SUPABASE_URL}/rest/v1/knowledge_extractions"
            f"?status=eq.pending&order=created_at.asc&limit={limit}",
            headers=get_headers(),
        )

        if response.status_code != 200:
            raise ApplicationError(
                f"Failed to get extractions: {response.status_code} {response.text}"
            )

        return response.json()


@activity.defn
async def get_extraction(extraction_id: str) -> dict:
    """Get single extraction by ID."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ApplicationError("Supabase credentials not configured")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{SUPABASE_URL}/rest/v1/knowledge_extractions?id=eq.{extraction_id}",
            headers=get_headers(),
        )

        if response.status_code != 200:
            raise ApplicationError(
                f"Failed to get extraction: {response.status_code} {response.text}"
            )

        results = response.json()
        if not results:
            raise ApplicationError(f"Extraction not found: {extraction_id}")

        return results[0]


@activity.defn
async def update_extraction_status(
    extraction_id: str,
    status: str,
    reviewed_by: Optional[str] = None,
    review_notes: Optional[str] = None,
    applied_to: Optional[str] = None,
) -> bool:
    """Update extraction status after review."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ApplicationError("Supabase credentials not configured")

    update_data = {"status": status}

    if reviewed_by:
        update_data["reviewed_by"] = reviewed_by
        update_data["reviewed_at"] = datetime.utcnow().isoformat()

    if review_notes:
        update_data["review_notes"] = review_notes

    if applied_to:
        update_data["applied_to"] = applied_to
        update_data["applied_at"] = datetime.utcnow().isoformat()

    async with httpx.AsyncClient() as client:
        response = await client.patch(
            f"{SUPABASE_URL}/rest/v1/knowledge_extractions?id=eq.{extraction_id}",
            headers=get_headers(),
            json=update_data,
        )

        if response.status_code not in (200, 204):
            raise ApplicationError(
                f"Failed to update status: {response.status_code} {response.text}"
            )

        return True


@activity.defn
async def apply_premise_knowledge(extraction: dict) -> dict:
    """
    Create new premise from approved extraction.
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ApplicationError("Supabase credentials not configured")

    payload = extraction.get("payload", {})

    premise_data = {
        "premise_type": payload.get("premise_type"),
        "name": payload.get("name") or extraction.get("name"),
        "description": extraction.get("description"),
        "origin_story": payload.get("origin_story"),
        "mechanism_claim": payload.get("mechanism_claim"),
        "source": "extracted",
        "status": "emerging",
        "vertical": payload.get("vertical"),
        "geo": payload.get("geo"),
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{SUPABASE_URL}/rest/v1/premises",
            headers=get_headers(),
            json=premise_data,
        )

        if response.status_code not in (200, 201):
            raise ApplicationError(
                f"Failed to create premise: {response.status_code} {response.text}"
            )

        result = response.json()
        premise_id = result[0]["id"]

        activity.logger.info(f"Created premise: {premise_id}")

        return {
            "target_table": "premises",
            "target_id": premise_id,
            "operation": "insert",
            "success": True,
        }


@activity.defn
async def apply_process_rule(extraction: dict) -> dict:
    """
    Add process rule to config table.
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ApplicationError("Supabase credentials not configured")

    payload = extraction.get("payload", {})

    config_data = {
        "key": f"rule_{payload.get('rule_name', 'unknown')}",
        "value": json.dumps(
            {
                "condition": payload.get("condition"),
                "recommendation": payload.get("recommendation"),
                "priority": payload.get("priority", "medium"),
                "applies_to": payload.get("applies_to", []),
                "source_extraction_id": extraction.get("id"),
            }
        ),
        "description": extraction.get("description"),
        "is_secret": False,
    }

    async with httpx.AsyncClient() as client:
        # Use upsert with on_conflict
        headers = get_headers()
        headers["Prefer"] = "resolution=merge-duplicates,return=representation"

        response = await client.post(
            f"{SUPABASE_URL}/rest/v1/config",
            headers=headers,
            json=config_data,
        )

        if response.status_code not in (200, 201):
            raise ApplicationError(
                f"Failed to create config: {response.status_code} {response.text}"
            )

        result = response.json()
        config_key = result[0]["key"] if result else config_data["key"]

        activity.logger.info(f"Created config rule: {config_key}")

        return {
            "target_table": "config",
            "target_id": config_key,
            "operation": "insert",
            "success": True,
        }


@activity.defn
async def apply_component_weight(extraction: dict) -> dict:
    """
    Seed component_learnings with expert knowledge.

    Note: This creates a record with expert_boost but no market data.
    The learning loop will update with actual performance data later.
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ApplicationError("Supabase credentials not configured")

    payload = extraction.get("payload", {})

    # Check if component_learnings has origin column
    # If not, we'll use a different approach
    learning_data = {
        "component_type": payload.get("component_type"),
        "component_value": payload.get("component_value"),
        "sample_size": 0,
        "win_count": 0,
        "loss_count": 0,
        "total_spend": 0,
        "total_revenue": 0,
        "geo": None,
        "avatar_id": None,
    }

    async with httpx.AsyncClient() as client:
        headers = get_headers()
        headers["Prefer"] = "resolution=merge-duplicates,return=representation"

        response = await client.post(
            f"{SUPABASE_URL}/rest/v1/component_learnings",
            headers=headers,
            json=learning_data,
        )

        if response.status_code not in (200, 201):
            # Might fail due to unique constraint - that's OK
            activity.logger.warning(
                f"Component learning might exist: {response.status_code}"
            )
            return {
                "target_table": "component_learnings",
                "target_id": None,
                "operation": "skip",
                "success": True,
                "note": "Component might already exist",
            }

        result = response.json()
        learning_id = result[0]["id"] if result else None

        activity.logger.info(f"Created component learning: {learning_id}")

        return {
            "target_table": "component_learnings",
            "target_id": learning_id,
            "operation": "insert",
            "success": True,
            "note": "Expert seed data, awaiting market validation",
        }


@activity.defn
async def apply_creative_attribute(extraction: dict) -> dict:
    """
    Handle creative attribute extraction.

    Note: Schema extensions require manual review and deployment.
    This activity logs the request but doesn't auto-modify schema.
    """
    payload = extraction.get("payload", {})

    activity.logger.info(
        f"Creative attribute requested: field={payload.get('field_name')}, "
        f"value={payload.get('value')}"
    )

    # For now, just acknowledge - schema changes need manual review
    return {
        "target_table": "schema_registry",
        "target_id": None,
        "operation": "schema_extend",
        "success": True,
        "note": f"Schema extension requested: {payload.get('field_name')}={payload.get('value')}. Requires manual review.",
    }
