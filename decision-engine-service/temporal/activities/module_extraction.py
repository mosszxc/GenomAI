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
from src.core.http_client import get_http_client

from temporal.tracing import get_activity_logger

# Schema name for all operations
SCHEMA = "genomai"

# Module type definitions with fields to extract from decomposed payload
# Based on 7 Independent Variables (see VISION.md and issue #596)
#
# Each module type has:
#   - primary_field: The main field to extract
#   - fallback_field: Alternative field if primary is missing
#   - related_fields: Additional context fields to store in content
#   - key_fields: Fields used for deduplication hash
#   - text_field: Optional field for human-readable text_content
MODULE_FIELDS = {
    "hook_mechanism": {
        "primary_field": "hook_mechanism",
        "fallback_field": "opening_type",
        "related_fields": ["hooks", "hook_stopping_power"],
        "key_fields": ["hook_mechanism"],
        "text_field": "hooks",
    },
    "angle_type": {
        "primary_field": "angle_type",
        "fallback_field": "emotional_trigger",
        "related_fields": [],
        "key_fields": ["angle_type"],
        "text_field": None,
    },
    "message_structure": {
        "primary_field": "message_structure",
        "fallback_field": "story_type",
        "related_fields": [],
        "key_fields": ["message_structure"],
        "text_field": None,
    },
    "ump_type": {
        "primary_field": "ump_type",
        "fallback_field": "ums_type",
        "related_fields": ["core_belief"],
        "key_fields": ["ump_type"],
        "text_field": None,
    },
    "promise_type": {
        "primary_field": "promise_type",
        "fallback_field": None,  # Fallback uses state_before + state_after
        "fallback_composite": ["state_before", "state_after"],
        "related_fields": ["state_before", "state_after"],
        "key_fields": ["promise_type"],
        "text_field": None,
    },
    "proof_type": {
        "primary_field": "proof_type",
        "fallback_field": "proof_source",
        "related_fields": ["social_proof_pattern"],
        "key_fields": ["proof_type"],
        "text_field": None,
    },
    "cta_style": {
        "primary_field": "cta_style",
        "fallback_field": "risk_reversal_type",
        "related_fields": [],
        "key_fields": ["cta_style"],
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

    Uses primary_field value for deduplication. If fallback was used,
    the value is still stored under primary_field name.

    Args:
        module_type: One of 7 module types
        content: Module content dict (with primary_field value)

    Returns:
        SHA256 hex digest
    """
    config = MODULE_FIELDS[module_type]
    primary_field = config["primary_field"]

    # Build canonical dict with primary field only
    # Note: content already has value under primary_field (even if fallback was used)
    canonical = {primary_field: content.get(primary_field)}

    # Sort keys and serialize for consistent hashing
    canonical_str = json.dumps(canonical, sort_keys=True)

    return hashlib.sha256(canonical_str.encode()).hexdigest()


def extract_module_content(payload: dict, module_type: str) -> Dict[str, Any]:
    """
    Extract module content from decomposed payload with fallback support.

    Uses primary_field first, then fallback_field or fallback_composite.
    Also includes related_fields for additional context.

    Args:
        payload: Decomposed creative payload
        module_type: One of 7 module types (hook_mechanism, angle_type, etc.)

    Returns:
        Dict with extracted fields for this module type
    """
    config = MODULE_FIELDS[module_type]
    primary_field = config["primary_field"]
    fallback_field = config.get("fallback_field")
    fallback_composite = config.get("fallback_composite", [])
    related_fields = config.get("related_fields", [])

    content: Dict[str, Any] = {}

    # 1. Try primary field first
    if primary_field in payload and payload[primary_field]:
        content[primary_field] = payload[primary_field]
    # 2. Try fallback field
    elif fallback_field and fallback_field in payload and payload[fallback_field]:
        # Store under primary field name for consistency
        content[primary_field] = payload[fallback_field]
        content["_fallback_used"] = fallback_field
    # 3. Try composite fallback (e.g., state_before + state_after -> promise_type)
    elif fallback_composite:
        composite_values = [payload.get(f) for f in fallback_composite if payload.get(f)]
        if composite_values:
            content[primary_field] = " → ".join(str(v) for v in composite_values)
            content["_fallback_used"] = "+".join(fallback_composite)

    # 4. Add related fields for context
    for field in related_fields:
        if field in payload and payload[field]:
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

    client = get_http_client()
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
    client = get_http_client()
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

    # Use on_conflict for idempotent retry handling (Issue #579)
    # UNIQUE constraint: (module_type, module_key)
    upsert_headers = {
        **headers,
        "Prefer": "resolution=ignore-duplicates,return=representation",
    }
    response = await client.post(
        f"{rest_url}/module_bank?on_conflict=module_type,module_key",
        headers=upsert_headers,
        json=module,
    )
    response.raise_for_status()
    data = response.json()

    if not data:
        # Conflict occurred (retry case) - fetch existing module
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
            log = get_activity_logger(module_type=module_type)
            log.info("Module already exists (retry case)", module_id=existing[0]["id"])
            return existing[0]
        raise RuntimeError("Failed to insert module: no data returned")

    log = get_activity_logger(module_type=module_type)
    log.info("Created new module", module_id=data[0]["id"])
    return data[0]


# All 7 module types in extraction order
MODULE_TYPES = [
    "hook_mechanism",
    "angle_type",
    "message_structure",
    "ump_type",
    "promise_type",
    "proof_type",
    "cta_style",
]


@activity.defn
async def extract_modules_from_decomposition(
    creative_id: str,
    decomposed_id: str,
    payload: Dict[str, Any],
    vertical: Optional[str] = None,
    geo: Optional[str] = None,
) -> Dict[str, Optional[str]]:
    """
    Extract all 7 module types from decomposed payload.

    Main activity for Modular Creative System.

    7 Variables (from VISION.md):
    1. hook_mechanism - How to grab attention
    2. angle_type - Emotional angle/trigger
    3. message_structure - Narrative structure
    4. ump_type - Unique mechanism promise
    5. promise_type - Type of promise made
    6. proof_type - Type of proof/social validation
    7. cta_style - Call to action style

    Cold Start Strategy:
    - New modules inherit metrics from source creative
    - Deduplication by module_key (SHA256 hash)

    Args:
        creative_id: Source creative UUID
        decomposed_id: Decomposed creative UUID
        payload: Decomposed creative payload
        vertical: Optional target vertical
        geo: Optional target GEO

    Returns:
        Dict with module IDs for each type:
        {
            "hook_mechanism_id": uuid,
            "angle_type_id": uuid,
            "message_structure_id": uuid,
            "ump_type_id": uuid,
            "promise_type_id": uuid,
            "proof_type_id": uuid,
            "cta_style_id": uuid,
        }
    """
    log = get_activity_logger(
        creative_id=creative_id,
        decomposed_id=decomposed_id,
        vertical=vertical,
        geo=geo,
    )
    log.info("Extracting 7 module types from decomposition")

    # 1. Get parent creative metrics for cold start
    metrics = await get_creative_metrics(creative_id)
    log.info("Source creative metrics loaded", metrics=metrics)

    # Initialize result with all 7 module types
    result: Dict[str, Optional[str]] = {f"{mt}_id": None for mt in MODULE_TYPES}

    extracted_count = 0

    # 2. Extract each module type
    for module_type in MODULE_TYPES:
        # Extract content from payload (with fallback support)
        content = extract_module_content(payload, module_type)

        # Get primary field to check for meaningful content
        primary_field = MODULE_FIELDS[module_type]["primary_field"]

        # Skip if no primary field value extracted
        if not content.get(primary_field):
            log.debug("No content for module type", module_type=module_type)
            continue

        # Compute deduplication key
        module_key = compute_module_key(module_type, content)

        # Get text content for human readability
        text_content = get_text_content(payload, module_type)

        # Log if fallback was used
        if "_fallback_used" in content:
            log.info(
                "Used fallback for module",
                module_type=module_type,
                fallback=content["_fallback_used"],
            )

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
        extracted_count += 1

    log.info(
        "Module extraction complete",
        extracted_count=extracted_count,
        total_types=len(MODULE_TYPES),
        modules=result,
    )
    return result
