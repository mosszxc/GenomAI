"""
Avatar Service

Handles avatar CRUD operations for Idea Registry.
Uses the same pattern as learning_loop.py for Supabase access.
"""

import os
from src.core.http_client import get_http_client
from typing import Optional, Tuple

from src.utils.errors import SupabaseError
from src.utils.hashing import compute_avatar_hash


SCHEMA = "genomai"


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


async def find_avatar_by_hash(canonical_hash: str) -> Optional[dict]:
    """
    Find avatar by canonical_hash.

    Args:
        canonical_hash: MD5 hash of avatar fields

    Returns:
        Avatar dict if found, None otherwise
    """
    if not canonical_hash:
        return None

    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    client = get_http_client()
    response = await client.get(
        f"{rest_url}/avatars"
        f"?canonical_hash=eq.{canonical_hash}"
        f"&select=id,canonical_hash,vertical,geo,deep_desire_type,primary_trigger,awareness_level,status",
        headers=headers,
    )
    response.raise_for_status()
    data = response.json()

    if data and len(data) > 0:
        return data[0]

    return None


async def create_avatar(
    canonical_hash: str,
    vertical: str,
    geo: str,
    deep_desire_type: str,
    primary_trigger: str,
    awareness_level: str,
    status: str = "emerging",
) -> dict:
    """
    Create new avatar record.

    Args:
        canonical_hash: MD5 hash
        vertical: Buyer vertical
        geo: Buyer geo
        deep_desire_type: Avatar field
        primary_trigger: Avatar field
        awareness_level: Avatar field
        status: Initial status (default: emerging)

    Returns:
        Created avatar dict

    Raises:
        SupabaseError: If creation fails (e.g., duplicate hash)
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)

    # Generate name in same format as n8n: "vertical | deep_desire_type | awareness_level"
    name = f"{vertical} | {deep_desire_type} | {awareness_level}"

    client = get_http_client()
    response = await client.post(
        f"{rest_url}/avatars",
        headers=headers,
        json={
            "canonical_hash": canonical_hash,
            "name": name,
            "vertical": vertical,
            "geo": geo,
            "deep_desire_type": deep_desire_type,
            "primary_trigger": primary_trigger,
            "awareness_level": awareness_level,
            "status": status,
        },
    )

    if response.status_code == 409:
        # Duplicate key - race condition, try to find existing
        existing = await find_avatar_by_hash(canonical_hash)
        if existing:
            return existing
        raise SupabaseError(
            f"Avatar with hash {canonical_hash} already exists but not found"
        )

    response.raise_for_status()
    data = response.json()

    if data and len(data) > 0:
        return data[0]

    raise SupabaseError("Failed to create avatar: no data returned")


async def find_or_create_avatar(
    vertical: str,
    geo: str,
    deep_desire_type: Optional[str],
    primary_trigger: Optional[str],
    awareness_level: Optional[str],
) -> Tuple[Optional[str], Optional[str]]:
    """
    Find existing avatar or create new one.

    Args:
        vertical: Buyer vertical
        geo: Buyer geo
        deep_desire_type: Avatar field (required for avatar creation)
        primary_trigger: Avatar field (required for avatar creation)
        awareness_level: Avatar field (required for avatar creation)

    Returns:
        Tuple of (avatar_id, status) where:
        - avatar_id: UUID string or None if avatar fields missing
        - status: 'existing', 'new', or None if no avatar
    """
    # Compute avatar hash - returns None if required fields missing
    # Issue #194: geo now included in avatar hash for geo-specific avatars
    avatar_hash = compute_avatar_hash(
        vertical=vertical,
        geo=geo,
        deep_desire_type=deep_desire_type,
        primary_trigger=primary_trigger,
        awareness_level=awareness_level,
    )

    if not avatar_hash:
        # Cannot create avatar without required fields
        return None, None

    # Try to find existing
    existing = await find_avatar_by_hash(avatar_hash)
    if existing:
        return existing["id"], "existing"

    # Create new avatar
    new_avatar = await create_avatar(
        canonical_hash=avatar_hash,
        vertical=vertical,
        geo=geo,
        deep_desire_type=deep_desire_type,
        primary_trigger=primary_trigger,
        awareness_level=awareness_level,
    )

    return new_avatar["id"], "new"
