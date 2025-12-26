"""
Idea Registry Service

Main business logic for registering ideas from decomposed creatives.
Ported from n8n idea_registry_create workflow.

Flow:
1. Load decomposed_creative by creative_id
2. Load buyer linked to creative
3. Compute canonical_hash from payload
4. Find or create idea
5. Find or create avatar
6. Link idea to decomposed_creative
7. Emit IdeaRegistered event
8. Return result
"""

import os
import json
import httpx
from typing import Optional
from dataclasses import dataclass

from src.utils.errors import SupabaseError
from src.utils.hashing import compute_canonical_hash
from src.services.avatar_service import find_or_create_avatar


SCHEMA = "genomai"


@dataclass
class IdeaRegistryResult:
    """Result of idea registration"""
    idea_id: str
    status: str  # 'new' or 'reused'
    canonical_hash: str
    avatar_id: Optional[str] = None
    avatar_status: Optional[str] = None  # 'new', 'existing', or None

    def to_dict(self) -> dict:
        return {
            "idea_id": self.idea_id,
            "status": self.status,
            "canonical_hash": self.canonical_hash,
            "avatar_id": self.avatar_id,
            "avatar_status": self.avatar_status
        }


class IdeaRegistryError(Exception):
    """Error during idea registration"""
    pass


class DecomposedCreativeNotFoundError(IdeaRegistryError):
    """Decomposed creative not found for creative_id"""
    pass


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
        "Content-Type": "application/json"
    }
    if for_write:
        headers["Content-Profile"] = SCHEMA
        headers["Prefer"] = "return=representation"
    return headers


async def load_decomposed_creative(creative_id: str) -> Optional[dict]:
    """
    Load decomposed_creative by creative_id.

    Args:
        creative_id: UUID of the creative

    Returns:
        Decomposed creative dict or None if not found
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{rest_url}/decomposed_creatives"
            f"?creative_id=eq.{creative_id}"
            f"&select=id,creative_id,payload,idea_id",
            headers=headers
        )
        response.raise_for_status()
        data = response.json()

        if data and len(data) > 0:
            return data[0]

        return None


async def load_buyer_by_creative(creative_id: str) -> Optional[dict]:
    """
    Load buyer linked to creative via creatives.buyer_id.

    Args:
        creative_id: UUID of the creative

    Returns:
        Buyer dict or None if not found
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    async with httpx.AsyncClient() as client:
        # First get creative to get buyer_id
        response = await client.get(
            f"{rest_url}/creatives"
            f"?id=eq.{creative_id}"
            f"&select=buyer_id",
            headers=headers
        )
        response.raise_for_status()
        creative_data = response.json()

        if not creative_data or not creative_data[0].get('buyer_id'):
            return None

        buyer_id = creative_data[0]['buyer_id']

        # Load buyer by telegram_id (buyer_id in creatives is telegram_id)
        response = await client.get(
            f"{rest_url}/buyers"
            f"?telegram_id=eq.{buyer_id}"
            f"&select=id,telegram_id,vertical,geo",
            headers=headers
        )
        response.raise_for_status()
        buyer_data = response.json()

        if buyer_data and len(buyer_data) > 0:
            return buyer_data[0]

        return None


async def find_idea_by_hash(canonical_hash: str) -> Optional[dict]:
    """
    Find idea by canonical_hash.

    Args:
        canonical_hash: SHA256 hash of canonical fields

    Returns:
        Idea dict or None if not found
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{rest_url}/ideas"
            f"?canonical_hash=eq.{canonical_hash}"
            f"&select=id,canonical_hash,avatar_id,status",
            headers=headers
        )
        response.raise_for_status()
        data = response.json()

        if data and len(data) > 0:
            return data[0]

        return None


async def create_idea(
    canonical_hash: str,
    avatar_id: Optional[str] = None,
    status: str = "active"
) -> dict:
    """
    Create new idea record.

    Args:
        canonical_hash: SHA256 hash
        avatar_id: Optional linked avatar ID
        status: Initial status (default: active)

    Returns:
        Created idea dict
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)

    payload = {
        "canonical_hash": canonical_hash,
        "status": status
    }
    if avatar_id:
        payload["avatar_id"] = avatar_id

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{rest_url}/ideas",
            headers=headers,
            json=payload
        )

        if response.status_code == 409:
            # Duplicate key - race condition, try to find existing
            existing = await find_idea_by_hash(canonical_hash)
            if existing:
                return existing
            raise SupabaseError(f"Idea with hash {canonical_hash} already exists but not found")

        response.raise_for_status()
        data = response.json()

        if data and len(data) > 0:
            return data[0]

        raise SupabaseError("Failed to create idea: no data returned")


async def link_idea_to_decomposed(decomposed_id: str, idea_id: str) -> None:
    """
    Update decomposed_creative.idea_id.

    Args:
        decomposed_id: UUID of decomposed_creative
        idea_id: UUID of idea to link
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)
    headers["Prefer"] = "return=minimal"

    async with httpx.AsyncClient() as client:
        response = await client.patch(
            f"{rest_url}/decomposed_creatives?id=eq.{decomposed_id}",
            headers=headers,
            json={"idea_id": idea_id}
        )
        response.raise_for_status()


async def emit_idea_registered_event(
    idea_id: str,
    status: str,
    avatar_id: Optional[str] = None
) -> None:
    """
    Emit IdeaRegistered event to event_log.

    Args:
        idea_id: UUID of registered idea
        status: 'new' or 'reuse'
        avatar_id: Optional linked avatar ID
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)

    payload = {"source": status}
    if avatar_id:
        payload["avatar_id"] = avatar_id

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{rest_url}/event_log",
            headers=headers,
            json={
                "event_type": "IdeaRegistered",
                "entity_type": "idea",
                "entity_id": idea_id,
                "payload": payload
            }
        )
        response.raise_for_status()


async def register_idea(creative_id: str, schema_version: str = "v1") -> IdeaRegistryResult:
    """
    Register idea for a creative.

    Main entry point - ported from n8n idea_registry_create workflow.

    Flow:
    1. Load decomposed_creative by creative_id
    2. Load buyer linked to creative
    3. Parse payload from decomposed_creative
    4. Compute canonical_hash from payload
    5. Find or create idea by canonical_hash
    6. Find or create avatar
    7. Link idea to decomposed_creative
    8. Emit IdeaRegistered event
    9. Return result

    Args:
        creative_id: UUID of the creative
        schema_version: Schema version (default: v1)

    Returns:
        IdeaRegistryResult with idea_id, status, etc.

    Raises:
        DecomposedCreativeNotFoundError: If decomposed creative not found
        IdeaRegistryError: If registration fails
    """
    # Step 1: Load decomposed creative
    decomposed = await load_decomposed_creative(creative_id)
    if not decomposed:
        raise DecomposedCreativeNotFoundError(
            f"Decomposed creative not found for creative_id: {creative_id}"
        )

    # Step 2: Load buyer
    buyer = await load_buyer_by_creative(creative_id)
    vertical = buyer.get('vertical', 'unknown') if buyer else 'unknown'
    geo = buyer.get('geo', 'unknown') if buyer else 'unknown'

    # Step 3: Parse payload
    payload = decomposed.get('payload', {})
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError as e:
            raise IdeaRegistryError(f"Failed to parse payload: {e}")

    # Step 4: Compute canonical hash
    canonical_hash = compute_canonical_hash(payload)

    # Step 5: Find or create idea
    existing_idea = await find_idea_by_hash(canonical_hash)

    if existing_idea:
        idea_id = existing_idea['id']
        idea_status = 'reused'
    else:
        # First create/find avatar, then create idea with avatar_id
        # Step 6a: Find or create avatar (before idea)
        avatar_id, avatar_status = await find_or_create_avatar(
            vertical=vertical,
            geo=geo,
            deep_desire_type=payload.get('deep_desire_type'),
            primary_trigger=payload.get('primary_trigger'),
            awareness_level=payload.get('awareness_level')
        )

        # Create idea with avatar linked
        new_idea = await create_idea(
            canonical_hash=canonical_hash,
            avatar_id=avatar_id
        )
        idea_id = new_idea['id']
        idea_status = 'new'

        # Step 7: Link idea to decomposed
        await link_idea_to_decomposed(decomposed['id'], idea_id)

        # Step 8: Emit event
        await emit_idea_registered_event(idea_id, idea_status, avatar_id)

        return IdeaRegistryResult(
            idea_id=idea_id,
            status=idea_status,
            canonical_hash=canonical_hash,
            avatar_id=avatar_id,
            avatar_status=avatar_status
        )

    # For reused idea, still need to link and emit
    # Step 6b: Get avatar info from existing idea
    avatar_id = existing_idea.get('avatar_id')
    avatar_status = 'existing' if avatar_id else None

    # Step 7: Link idea to decomposed
    await link_idea_to_decomposed(decomposed['id'], idea_id)

    # Step 8: Emit event
    await emit_idea_registered_event(idea_id, idea_status, avatar_id)

    return IdeaRegistryResult(
        idea_id=idea_id,
        status=idea_status,
        canonical_hash=canonical_hash,
        avatar_id=avatar_id,
        avatar_status=avatar_status
    )
