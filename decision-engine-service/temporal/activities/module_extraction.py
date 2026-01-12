"""
Module Extraction Activity

Temporal activity for extracting Hook, Promise, Proof modules from decomposed payload.
Implements cold start strategy: new modules inherit metrics from source creative.
Deduplication via SHA256 module_key hash.

Part of Modular Creative System (Phase 2).
"""

import os
import json
import hashlib
from typing import Optional, Dict, Any
from temporalio import activity
import httpx

from temporal.tracing import get_activity_logger

# Schema name for all operations
SCHEMA = "genomai"

# Module type definitions with fields to extract from decomposed payload
# Based on Canonical Schema v2 (see MODULAR_CREATIVE_SYSTEM.md)
MODULE_FIELDS = {
    "hook": {
        "fields": ["hooks", "hook_mechanism", "hook_stopping_power", "opening_type"],
        "key_fields": ["hook_mechanism", "opening_type"],
        "text_field": "hooks",  # For human-readable text_content
    },
    "promise": {
        "fields": [
            "promise_type",
            "core_belief",
            "state_before",
            "state_after",
            "ump_type",
            "ums_type",
        ],
        "key_fields": ["promise_type", "core_belief", "state_before", "state_after"],
        "text_field": None,
    },
    "proof": {
        "fields": ["proof_type", "proof_source", "social_proof_pattern", "story_type"],
        "key_fields": ["proof_type", "proof_source"],
        "text_field": None,
    },
}


def _get_credentials() -> tuple[str, str]:
    """Get Supabase credentials from environment."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        raise RuntimeError("Missing Supabase credentials")

    rest_url = f"{supabase_url}/rest/v1"
    return rest_url, supabase_key


def _get_headers(supabase_key: str, for_write: bool = False) -> dict:
    """Get headers for Supabase REST API with genomai schema."""
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Accept-Profile": SCHEMA,
        "Content-Type": "application/json",
    }
    if for_write:
        headers["Content-Profile"] = SCHEMA
        headers["Prefer"] = "return=representation"
    return headers


def compute_module_key(module_type: str, content: dict) -> str:
    """
    Compute SHA256 hash for module deduplication.

    Uses only key_fields defined in MODULE_FIELDS to ensure
    semantically identical modules get the same key.

    Args:
        module_type: hook, promise, or proof
        content: Module content dict

    Returns:
        SHA256 hex digest
    """
    key_fields = MODULE_FIELDS[module_type]["key_fields"]

    # Build canonical dict with only key fields
    canonical = {field: content.get(field) for field in key_fields}

    # Sort keys and serialize for consistent hashing
    canonical_str = json.dumps(canonical, sort_keys=True)

    return hashlib.sha256(canonical_str.encode()).hexdigest()


def extract_module_content(payload: dict, module_type: str) -> Dict[str, Any]:
    """
    Extract module content from decomposed payload.

    Args:
        payload: Decomposed creative payload (Canonical Schema v2)
        module_type: hook, promise, or proof

    Returns:
        Dict with extracted fields for this module type
    """
    fields = MODULE_FIELDS[module_type]["fields"]

    content = {}
    for field in fields:
        if field in payload:
            content[field] = payload[field]

    return content


def get_text_content(payload: dict, module_type: str) -> Optional[str]:
    """
    Extract human-readable text content for module.

    Args:
        payload: Decomposed creative payload
        module_type: hook, promise, or proof

    Returns:
        Text content string or None
    """
    text_field = MODULE_FIELDS[module_type].get("text_field")
    if not text_field:
        return None

    value = payload.get(text_field)

    # Handle array fields (e.g., hooks is a list)
    if isinstance(value, list):
        return "; ".join(str(v) for v in value if v)

    return str(value) if value else None


@activity.defn
async def get_creative_metrics(creative_id: str) -> Dict[str, Any]:
    """
    Get aggregated metrics for creative from outcome_aggregates.

    Used for cold start: new modules inherit metrics from source creative.

    Args:
        creative_id: Creative UUID

    Returns:
        Dict with sample_size, win_count, loss_count, total_spend, total_revenue
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    async with httpx.AsyncClient() as client:
        # Get latest outcome aggregate for this creative
        response = await client.get(
            f"{rest_url}/outcome_aggregates"
            f"?creative_id=eq.{creative_id}"
            f"&select=impressions,conversions,spend,cpa"
            f"&order=created_at.desc"
            f"&limit=1",
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()

        if not data:
            # No metrics yet - return zeros
            return {
                "sample_size": 0,
                "win_count": 0,
                "loss_count": 0,
                "total_spend": 0,
                "total_revenue": 0,
            }

        metrics = data[0]
        impressions = metrics.get("impressions", 0) or 0
        conversions = metrics.get("conversions", 0) or 0
        spend = float(metrics.get("spend", 0) or 0)
        cpa = float(metrics.get("cpa", 0) or 0)

        # Estimate revenue from conversions (simplified)
        # In production, this should come from actual revenue data
        estimated_revenue = conversions * cpa if cpa > 0 else 0

        # Simple win/loss heuristic: win if CPA below threshold
        # This is a placeholder - real logic should use actual test results
        is_win = cpa > 0 and cpa < 50  # Placeholder threshold

        return {
            "sample_size": impressions,
            "win_count": conversions if is_win else 0,
            "loss_count": conversions if not is_win else 0,
            "total_spend": spend,
            "total_revenue": estimated_revenue,
        }


@activity.defn
async def upsert_module(
    module_type: str,
    module_key: str,
    content: Dict[str, Any],
    text_content: Optional[str],
    source_creative_id: str,
    source_decomposed_id: str,
    vertical: Optional[str],
    geo: Optional[str],
    metrics: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Upsert module to module_bank with deduplication.

    ON CONFLICT (module_type, module_key) DO UPDATE:
    - Keeps first source_creative_id (discovery tracking)
    - Updates metrics if new creative has more data

    Args:
        module_type: hook, promise, or proof
        module_key: SHA256 hash for deduplication
        content: Module content JSONB
        text_content: Human-readable text
        source_creative_id: Creative that produced this module
        source_decomposed_id: Decomposed creative that produced this module
        vertical: Target vertical
        geo: Target GEO
        metrics: Inherited metrics from source creative

    Returns:
        Upserted module dict
    """
    import uuid

    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)

    # Check if module already exists
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{rest_url}/module_bank"
            f"?module_type=eq.{module_type}"
            f"&module_key=eq.{module_key}"
            f"&select=id,sample_size",
            headers=_get_headers(supabase_key),
        )
        response.raise_for_status()
        existing = response.json()

        if existing:
            # Module exists - only update if new creative has more data
            existing_module = existing[0]
            existing_sample = existing_module.get("sample_size", 0) or 0
            new_sample = metrics.get("sample_size", 0) or 0

            if new_sample > existing_sample:
                # Update with newer metrics
                response = await client.patch(
                    f"{rest_url}/module_bank?id=eq.{existing_module['id']}",
                    headers=headers,
                    json={
                        "sample_size": new_sample,
                        "win_count": metrics.get("win_count", 0),
                        "loss_count": metrics.get("loss_count", 0),
                        "total_spend": metrics.get("total_spend", 0),
                        "total_revenue": metrics.get("total_revenue", 0),
                    },
                )
                response.raise_for_status()
                log = get_activity_logger(module_type=module_type)
                log.info(
                    "Updated module with new metrics",
                    module_id=existing_module["id"],
                    new_sample_size=new_sample,
                )

            return existing_module

        # Insert new module
        module = {
            "id": str(uuid.uuid4()),
            "module_type": module_type,
            "module_key": module_key,
            "content": json.dumps(content),
            "source_creative_id": source_creative_id,
            "source_decomposed_id": source_decomposed_id,
            "sample_size": metrics.get("sample_size", 0),
            "win_count": metrics.get("win_count", 0),
            "loss_count": metrics.get("loss_count", 0),
            "total_spend": metrics.get("total_spend", 0),
            "total_revenue": metrics.get("total_revenue", 0),
            "status": "emerging",
        }

        if text_content:
            module["text_content"] = text_content
        if vertical:
            module["vertical"] = vertical
        if geo:
            module["geo"] = geo

        response = await client.post(
            f"{rest_url}/module_bank",
            headers=headers,
            json=module,
        )
        response.raise_for_status()
        data = response.json()

        if not data:
            raise RuntimeError("Failed to insert module: no data returned")

        log = get_activity_logger(module_type=module_type)
        log.info("Created new module", module_id=data[0]["id"])
        return data[0]


@activity.defn
async def extract_modules_from_decomposition(
    creative_id: str,
    decomposed_id: str,
    payload: Dict[str, Any],
    vertical: Optional[str] = None,
    geo: Optional[str] = None,
) -> Dict[str, Optional[str]]:
    """
    Extract Hook, Promise, Proof modules from decomposed payload.

    Main activity for Modular Creative System Phase 2.

    Cold Start Strategy:
    - New modules inherit metrics from source creative
    - Deduplication by module_key (SHA256 hash)

    Args:
        creative_id: Source creative UUID
        decomposed_id: Decomposed creative UUID
        payload: Decomposed creative payload (Canonical Schema v2)
        vertical: Optional target vertical
        geo: Optional target GEO

    Returns:
        Dict with module IDs: {"hook_id": uuid, "promise_id": uuid, "proof_id": uuid}
    """
    log = get_activity_logger(
        creative_id=creative_id,
        decomposed_id=decomposed_id,
        vertical=vertical,
        geo=geo,
    )
    log.info("Extracting modules from decomposition")

    # 1. Get parent creative metrics for cold start
    metrics = await get_creative_metrics(creative_id)
    log.info("Source creative metrics loaded", metrics=metrics)

    result = {
        "hook_id": None,
        "promise_id": None,
        "proof_id": None,
    }

    # 2. Extract each module type
    for module_type in ["hook", "promise", "proof"]:
        # Extract content from payload
        content = extract_module_content(payload, module_type)

        # Skip if no meaningful content
        if not content or all(v is None for v in content.values()):
            log.warning("No content for module type", module_type=module_type)
            continue

        # Compute deduplication key
        module_key = compute_module_key(module_type, content)

        # Get text content for human readability
        text_content = get_text_content(payload, module_type)

        # Upsert module
        module = await upsert_module(
            module_type=module_type,
            module_key=module_key,
            content=content,
            text_content=text_content,
            source_creative_id=creative_id,
            source_decomposed_id=decomposed_id,
            vertical=vertical,
            geo=geo,
            metrics=metrics,
        )

        result[f"{module_type}_id"] = module["id"]

    log.info(
        "Module extraction complete",
        hook_id=result["hook_id"],
        promise_id=result["promise_id"],
        proof_id=result["proof_id"],
    )
    return result
