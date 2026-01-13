"""
External Inspiration Service

Handles ingestion of external creatives from spy tools (AdHeart, FB Spy).
Part of Inspiration System to prevent creative degradation.

Flow:
1. Receive raw creative data from spy tool/parser
2. Store in external_inspirations table
3. LLM extracts components (reuses decomposition logic)
4. When system is stale, inject components into component_learnings

Issue: Inspiration System
"""

import os
from src.core.http_client import get_http_client
from typing import Optional, List
from dataclasses import dataclass
from datetime import datetime

from src.utils.errors import SupabaseError


SCHEMA = "genomai"


@dataclass
class ExternalInspiration:
    """External creative inspiration"""

    id: Optional[str]
    source_type: str  # adheart, fb_spy, manual, competitor
    source_url: Optional[str]
    source_id: Optional[str]
    raw_creative_data: dict
    extracted_components: Optional[dict]
    vertical: Optional[str]
    geo: Optional[str]
    estimated_performance: Optional[str]
    status: str  # pending, extracted, injected, rejected, expired


def _get_credentials():
    """Get Supabase credentials from environment"""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        raise SupabaseError("Missing Supabase credentials")

    rest_url = f"{supabase_url}/rest/v1"
    return rest_url, supabase_key


def _get_headers(supabase_key: str, for_write: bool = False) -> dict:
    """Get headers for Supabase REST API with schema"""
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


async def create_external_inspiration(
    source_type: str,
    raw_creative_data: dict,
    source_url: Optional[str] = None,
    source_id: Optional[str] = None,
    vertical: Optional[str] = None,
    geo: Optional[str] = None,
    estimated_performance: Optional[str] = None,
) -> dict:
    """
    Create new external inspiration record.

    Args:
        source_type: Source of inspiration (adheart, fb_spy, manual, competitor)
        raw_creative_data: Raw data from spy tool
        source_url: URL of the creative
        source_id: External system ID
        vertical: Optional vertical classification
        geo: Optional geo classification
        estimated_performance: Optional performance estimate (high, medium, low, unknown)

    Returns:
        Created inspiration record
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)

    payload = {
        "source_type": source_type,
        "raw_creative_data": raw_creative_data,
        "source_url": source_url,
        "source_id": source_id,
        "vertical": vertical,
        "geo": geo,
        "estimated_performance": estimated_performance or "unknown",
        "status": "pending",
    }
    # Remove None values
    payload = {k: v for k, v in payload.items() if v is not None}

    client = get_http_client()
    response = await client.post(
        f"{rest_url}/external_inspirations",
        headers=headers,
        json=payload,
    )
    response.raise_for_status()
    data = response.json()

    return data[0] if data else {}


async def update_external_inspiration(
    inspiration_id: str,
    extracted_components: Optional[dict] = None,
    status: Optional[str] = None,
    injection_trigger: Optional[str] = None,
    injected_components: Optional[dict] = None,
) -> dict:
    """
    Update external inspiration record.

    Args:
        inspiration_id: ID of inspiration to update
        extracted_components: LLM-extracted components
        status: New status
        injection_trigger: What triggered injection
        injected_components: Which components were injected

    Returns:
        Updated record
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)

    payload = {}
    if extracted_components is not None:
        payload["extracted_components"] = extracted_components
        payload["processed_at"] = datetime.utcnow().isoformat()
    if status is not None:
        payload["status"] = status
    if injection_trigger is not None:
        payload["injection_trigger"] = injection_trigger
    if injected_components is not None:
        payload["injected_components"] = injected_components
        payload["injected_at"] = datetime.utcnow().isoformat()

    if not payload:
        return {}

    client = get_http_client()
    response = await client.patch(
        f"{rest_url}/external_inspirations?id=eq.{inspiration_id}",
        headers=headers,
        json=payload,
    )
    response.raise_for_status()
    data = response.json()

    return data[0] if data else {}


async def get_pending_inspirations(limit: int = 10) -> List[dict]:
    """
    Get inspirations pending LLM extraction.

    Returns:
        List of pending inspiration records
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    client = get_http_client()
    response = await client.get(
        f"{rest_url}/external_inspirations?status=eq.pending&order=created_at.asc&limit={limit}",
        headers=headers,
    )
    response.raise_for_status()
    return response.json()


async def get_extracted_inspirations(limit: int = 10) -> List[dict]:
    """
    Get inspirations ready for injection (extracted but not injected).

    Returns:
        List of extracted inspiration records
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    client = get_http_client()
    response = await client.get(
        f"{rest_url}/external_inspirations?status=eq.extracted&order=created_at.asc&limit={limit}",
        headers=headers,
    )
    response.raise_for_status()
    return response.json()


async def inject_external_components(
    inspiration_id: str,
    target_avatar_id: Optional[str] = None,
    target_geo: Optional[str] = None,
    staleness_trigger: Optional[str] = None,
) -> List[dict]:
    """
    Inject extracted components from external inspiration into component_learnings.

    Args:
        inspiration_id: ID of inspiration to inject
        target_avatar_id: Target avatar (None = global)
        target_geo: Target geo
        staleness_trigger: What staleness signal triggered injection

    Returns:
        List of injected component_learning records
    """
    from src.services.cross_transfer import inject_component

    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    # Get inspiration
    client = get_http_client()
    response = await client.get(
        f"{rest_url}/external_inspirations?id=eq.{inspiration_id}",
        headers=headers,
    )
    response.raise_for_status()
    data = response.json()

    if not data:
        raise SupabaseError(f"Inspiration {inspiration_id} not found")

    inspiration = data[0]
    extracted = inspiration.get("extracted_components") or {}

    if not extracted:
        raise SupabaseError(f"Inspiration {inspiration_id} has no extracted components")

    # Trackable components to inject
    from src.services.component_learning import TRACKABLE_COMPONENTS

    injected = []
    injected_components = {}

    for component_type in TRACKABLE_COMPONENTS[:6]:
        component_value = extracted.get(component_type)
        if not component_value:
            continue

        try:
            result = await inject_component(
                component_type=component_type,
                component_value=component_value,
                target_avatar_id=target_avatar_id,
                target_geo=target_geo,
                origin_type="external_injection",
                origin_source_id=inspiration_id,
            )
            injected.append(result)
            injected_components[component_type] = component_value
        except Exception:
            # Continue with other components
            pass

    # Update inspiration status
    await update_external_inspiration(
        inspiration_id=inspiration_id,
        status="injected",
        injection_trigger=staleness_trigger,
        injected_components=injected_components,
    )

    return injected


async def get_inspiration_stats() -> dict:
    """
    Get statistics about external inspirations.

    Returns:
        dict with counts by status and source
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    client = get_http_client()
    # Get counts by status
    response = await client.get(
        f"{rest_url}/external_inspirations?select=status&limit=500",
        headers=headers,
    )
    response.raise_for_status()
    data = response.json()

    by_status = {}
    for row in data:
        status = row.get("status", "unknown")
        by_status[status] = by_status.get(status, 0) + 1

    # Get counts by source
    response = await client.get(
        f"{rest_url}/external_inspirations?select=source_type&limit=500",
        headers=headers,
    )
    response.raise_for_status()
    data = response.json()

    by_source = {}
    for row in data:
        source = row.get("source_type", "unknown")
        by_source[source] = by_source.get(source, 0) + 1

    total = sum(by_status.values())
    injected = by_status.get("injected", 0)

    return {
        "total": total,
        "by_status": by_status,
        "by_source": by_source,
        "injection_rate": injected / max(total, 1),
    }
