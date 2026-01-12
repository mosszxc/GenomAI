"""
Buyer Activities for Temporal Workflows

Activities for buyer management:
- create_buyer: Create new buyer record
- load_buyer: Load existing buyer by telegram_id
- update_buyer: Update buyer fields
- send_telegram_message: Send message to buyer
"""

import os
import uuid
from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass

from temporalio import activity
from temporalio.exceptions import ApplicationError
import httpx

from temporal.models.buyer import CreateBuyerInput


@dataclass
class BuyerRecord:
    """Buyer record from database."""

    id: str
    telegram_id: str
    telegram_username: Optional[str]
    name: str
    geos: Optional[List[str]]
    verticals: Optional[List[str]]
    keitaro_source: Optional[str]
    status: str
    created_at: str

    @classmethod
    def from_dict(cls, data: dict) -> "BuyerRecord":
        return cls(
            id=data["id"],
            telegram_id=data["telegram_id"],
            telegram_username=data.get("telegram_username"),
            name=data["name"],
            geos=data.get("geos"),
            verticals=data.get("verticals"),
            keitaro_source=data.get("keitaro_source"),
            status=data.get("status", "active"),
            created_at=data.get("created_at", ""),
        )


def _get_supabase_headers() -> dict:
    """Get headers for Supabase REST API."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        raise ApplicationError("Supabase credentials not configured")

    return {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Accept-Profile": "genomai",
        "Content-Profile": "genomai",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def _get_supabase_url() -> str:
    """Get Supabase REST URL."""
    url = os.getenv("SUPABASE_URL")
    if not url:
        raise ApplicationError("SUPABASE_URL not configured")
    return f"{url}/rest/v1"


@activity.defn
async def create_buyer(input: CreateBuyerInput) -> BuyerRecord:
    """
    Create a new buyer record in the database.

    Args:
        input: CreateBuyerInput with buyer data

    Returns:
        BuyerRecord with created buyer

    Raises:
        ApplicationError: If creation fails
    """
    activity.logger.info(f"Creating buyer for telegram_id: {input.telegram_id}")

    headers = _get_supabase_headers()
    base_url = _get_supabase_url()

    buyer_data = {
        "id": str(uuid.uuid4()),
        "telegram_id": input.telegram_id,
        "telegram_username": input.telegram_username,
        "name": input.name or f"Buyer_{input.telegram_id[:8]}",
        "geos": input.geos,
        "verticals": input.verticals,
        "keitaro_source": input.keitaro_source,
        "status": "active",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{base_url}/buyers",
            headers=headers,
            json=buyer_data,
            timeout=30.0,
        )

        if response.status_code == 409:
            # Already exists, load existing
            activity.logger.info("Buyer already exists, loading...")
            existing = await load_buyer_by_telegram_id(input.telegram_id)
            if existing:
                return existing
            raise ApplicationError("Buyer exists but could not be loaded")

        response.raise_for_status()
        data = response.json()

        if not data:
            raise ApplicationError("Failed to create buyer: empty response")

        created = data[0] if isinstance(data, list) else data
        activity.logger.info(f"Created buyer: {created['id']}")

        return BuyerRecord.from_dict(created)


@activity.defn
async def load_buyer_by_telegram_id(telegram_id: str) -> Optional[BuyerRecord]:
    """
    Load buyer by Telegram ID.

    Args:
        telegram_id: Telegram user ID

    Returns:
        BuyerRecord or None if not found
    """
    activity.logger.info(f"Loading buyer by telegram_id: {telegram_id}")

    headers = _get_supabase_headers()
    base_url = _get_supabase_url()

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{base_url}/buyers?telegram_id=eq.{telegram_id}&limit=1",
            headers=headers,
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()

        if not data:
            activity.logger.info(f"Buyer not found: {telegram_id}")
            return None

        return BuyerRecord.from_dict(data[0])


@activity.defn
async def load_buyer_by_id(buyer_id: str) -> Optional[BuyerRecord]:
    """
    Load buyer by ID.

    Args:
        buyer_id: Buyer UUID

    Returns:
        BuyerRecord or None if not found
    """
    activity.logger.info(f"Loading buyer by id: {buyer_id}")

    headers = _get_supabase_headers()
    base_url = _get_supabase_url()

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{base_url}/buyers?id=eq.{buyer_id}&limit=1",
            headers=headers,
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()

        if not data:
            activity.logger.info(f"Buyer not found: {buyer_id}")
            return None

        return BuyerRecord.from_dict(data[0])


@dataclass
class UpdateBuyerInput:
    """Input for update_buyer activity."""

    buyer_id: str
    name: Optional[str] = None
    geos: Optional[List[str]] = None
    verticals: Optional[List[str]] = None
    keitaro_source: Optional[str] = None
    status: Optional[str] = None


@activity.defn
async def update_buyer(input: UpdateBuyerInput) -> BuyerRecord:
    """
    Update buyer fields.

    Args:
        input: UpdateBuyerInput with fields to update

    Returns:
        Updated BuyerRecord
    """
    activity.logger.info(f"Updating buyer: {input.buyer_id}")

    headers = _get_supabase_headers()
    base_url = _get_supabase_url()

    update_data = {"updated_at": datetime.utcnow().isoformat()}

    if input.name is not None:
        update_data["name"] = input.name
    if input.geos is not None:
        update_data["geos"] = input.geos
    if input.verticals is not None:
        update_data["verticals"] = input.verticals
    if input.keitaro_source is not None:
        update_data["keitaro_source"] = input.keitaro_source
    if input.status is not None:
        update_data["status"] = input.status

    async with httpx.AsyncClient() as client:
        response = await client.patch(
            f"{base_url}/buyers?id=eq.{input.buyer_id}",
            headers=headers,
            json=update_data,
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()

        if not data:
            raise ApplicationError(f"Buyer not found: {input.buyer_id}")

        return BuyerRecord.from_dict(data[0])


@activity.defn
async def send_telegram_message(
    chat_id: str,
    text: str,
    parse_mode: str = "HTML",
    reply_markup: Optional[dict] = None,
) -> dict:
    """
    Send a message to Telegram chat.

    Args:
        chat_id: Telegram chat ID
        text: Message text
        parse_mode: HTML or Markdown
        reply_markup: Optional inline keyboard

    Returns:
        dict with message_id and status
    """
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        raise ApplicationError("TELEGRAM_BOT_TOKEN not configured")

    activity.logger.info(f"Sending message to chat: {chat_id}")

    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
    }

    if reply_markup:
        payload["reply_markup"] = reply_markup

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json=payload,
            timeout=30.0,
        )

        data = response.json()

        if not data.get("ok"):
            error = data.get("description", "Unknown Telegram error")
            activity.logger.error(f"Telegram error: {error}")
            raise ApplicationError(f"Telegram error: {error}")

        result = data.get("result", {})
        message_id = result.get("message_id")

        activity.logger.info(f"Message sent: {message_id}")

        return {
            "message_id": message_id,
            "chat_id": chat_id,
            "status": "sent",
        }


@dataclass
class LogInteractionInput:
    """Input for log_buyer_interaction activity."""

    telegram_id: str
    direction: str  # "in" or "out"
    message_type: str  # "bot", "user", "system", "command"
    content: str
    context: Optional[dict] = None
    buyer_id: Optional[str] = None


@activity.defn
async def log_buyer_interaction(input: LogInteractionInput) -> str:
    """
    Log interaction to buyer_interactions table.

    Args:
        input: LogInteractionInput with message data

    Returns:
        Created interaction ID
    """
    activity.logger.info(
        f"Logging interaction: {input.direction} {input.message_type} "
        f"for telegram_id={input.telegram_id}"
    )

    headers = _get_supabase_headers()
    base_url = _get_supabase_url()

    interaction_id = str(uuid.uuid4())
    payload = {
        "id": interaction_id,
        "telegram_id": input.telegram_id,
        "direction": input.direction,
        "message_type": input.message_type,
        "content": input.content[:2000]
        if input.content
        else "",  # Truncate long messages
        "context": input.context or {},
        "created_at": datetime.utcnow().isoformat(),
    }

    if input.buyer_id:
        payload["buyer_id"] = input.buyer_id

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{base_url}/buyer_interactions",
            headers=headers,
            json=payload,
            timeout=10.0,
        )
        # Don't fail workflow if logging fails
        if response.status_code >= 400:
            activity.logger.warning(
                f"Failed to log interaction: {response.status_code} {response.text}"
            )
            return ""

    activity.logger.info(f"Logged interaction: {interaction_id}")
    return interaction_id


@dataclass
class QueueHistoricalImportInput:
    """Input for queue_historical_import activity."""

    buyer_id: str
    campaign_id: str
    video_url: Optional[str] = None
    keitaro_source: Optional[str] = None
    metrics: Optional[dict] = None


@activity.defn
async def queue_historical_import(input: QueueHistoricalImportInput) -> str:
    """
    Queue a campaign for historical import processing.

    Args:
        input: Campaign data to queue

    Returns:
        Queue entry ID
    """
    activity.logger.info(
        f"Queueing historical import: campaign={input.campaign_id}, buyer={input.buyer_id}"
    )

    headers = _get_supabase_headers()
    # Use upsert to handle duplicate campaign_id
    headers["Prefer"] = "resolution=merge-duplicates,return=representation"
    base_url = _get_supabase_url()

    queue_entry = {
        "buyer_id": input.buyer_id,
        "campaign_id": input.campaign_id,
        "video_url": input.video_url,
        "keitaro_source": input.keitaro_source,
        "metrics": input.metrics,
        "status": "pending_video",
        "updated_at": datetime.utcnow().isoformat(),
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{base_url}/historical_import_queue?on_conflict=campaign_id",
            headers=headers,
            json=queue_entry,
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()

        entry_id = data[0]["id"] if data else "upserted"
        activity.logger.info(f"Queued historical import: {entry_id}")

        return entry_id


@activity.defn
async def get_pending_imports(buyer_id: str, limit: int = 10) -> List[dict]:
    """
    Get pending historical imports for a buyer.

    Args:
        buyer_id: Buyer UUID
        limit: Max records to fetch

    Returns:
        List of pending import records
    """
    activity.logger.info(f"Getting pending imports for buyer: {buyer_id}")

    headers = _get_supabase_headers()
    base_url = _get_supabase_url()

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{base_url}/historical_import_queue"
            f"?buyer_id=eq.{buyer_id}"
            f"&status=eq.pending"
            f"&order=created_at.asc"
            f"&limit={limit}",
            headers=headers,
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()

        activity.logger.info(f"Found {len(data)} pending imports")
        return data


@activity.defn
async def get_pending_video_campaigns(buyer_id: str) -> List[dict]:
    """
    Get campaigns waiting for video (status=pending_video) for onboarding.

    Args:
        buyer_id: Buyer UUID

    Returns:
        List of campaign records with metrics: [{id, campaign_id, metrics: {name, clicks, ...}}]
    """
    activity.logger.info(f"Getting pending video campaigns for buyer: {buyer_id}")

    headers = _get_supabase_headers()
    base_url = _get_supabase_url()

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{base_url}/historical_import_queue"
            f"?buyer_id=eq.{buyer_id}"
            f"&status=eq.pending_video"
            f"&order=created_at.asc"
            f"&select=id,campaign_id,metrics,status",
            headers=headers,
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()

        activity.logger.info(f"Found {len(data)} campaigns waiting for video")
        return data


@activity.defn
async def update_import_status(
    import_id: str,
    status: str,
    error_message: Optional[str] = None,
) -> None:
    """
    Update historical import status.

    Args:
        import_id: Import queue entry ID
        status: New status (pending, processing, completed, failed)
        error_message: Error message if failed
    """
    activity.logger.info(f"Updating import status: {import_id} -> {status}")

    headers = _get_supabase_headers()
    base_url = _get_supabase_url()

    update_data = {
        "status": status,
        "updated_at": datetime.utcnow().isoformat(),
    }

    if error_message:
        update_data["error_message"] = error_message

    async with httpx.AsyncClient() as client:
        await client.patch(
            f"{base_url}/historical_import_queue?id=eq.{import_id}",
            headers=headers,
            json=update_data,
            timeout=30.0,
        )

    activity.logger.info(f"Updated import status: {import_id}")


@dataclass
class ImportQueueRecord:
    """Import queue record from database."""

    id: str
    buyer_id: str
    campaign_id: str
    video_url: Optional[str]
    keitaro_source: Optional[str]
    metrics: Optional[dict]
    status: str
    created_at: str

    @classmethod
    def from_dict(cls, data: dict) -> "ImportQueueRecord":
        return cls(
            id=data["id"],
            buyer_id=data["buyer_id"],
            campaign_id=data["campaign_id"],
            video_url=data.get("video_url"),
            keitaro_source=data.get("keitaro_source"),
            metrics=data.get("metrics"),
            status=data.get("status", "pending"),
            created_at=data.get("created_at", ""),
        )


@activity.defn
async def get_import_by_campaign_id(
    campaign_id: str,
    buyer_id: str,
) -> Optional[ImportQueueRecord]:
    """
    Get historical import queue record by campaign ID and buyer ID.

    Search strategy:
    1. Try exact match (campaign_id + buyer_id)
    2. If not found, try campaign_id only (may have different buyer_id)
    3. Log detailed info for debugging

    Args:
        campaign_id: Keitaro campaign ID
        buyer_id: Buyer UUID

    Returns:
        ImportQueueRecord or None if not found
    """
    activity.logger.info(
        f"Getting import by campaign_id: {campaign_id}, buyer_id: {buyer_id}"
    )

    headers = _get_supabase_headers()
    base_url = _get_supabase_url()

    async with httpx.AsyncClient() as client:
        # Step 1: Try exact match (campaign_id + buyer_id)
        response = await client.get(
            f"{base_url}/historical_import_queue"
            f"?campaign_id=eq.{campaign_id}"
            f"&buyer_id=eq.{buyer_id}"
            f"&limit=1",
            headers=headers,
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()

        if data:
            activity.logger.info(f"Found import by exact match: {campaign_id}")
            return ImportQueueRecord.from_dict(data[0])

        # Step 2: Try campaign_id only (buyer_id mismatch scenario)
        activity.logger.info(
            f"Exact match not found, trying campaign_id only: {campaign_id}"
        )
        response = await client.get(
            f"{base_url}/historical_import_queue?campaign_id=eq.{campaign_id}&limit=1",
            headers=headers,
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()

        if data:
            record = data[0]
            actual_buyer_id = record.get("buyer_id")
            activity.logger.warning(
                f"Found import with different buyer_id: "
                f"campaign={campaign_id}, expected_buyer={buyer_id}, "
                f"actual_buyer={actual_buyer_id}"
            )
            # Return the record anyway - workflow can decide how to handle
            return ImportQueueRecord.from_dict(record)

        activity.logger.warning(
            f"Import queue record not found for campaign: {campaign_id} "
            f"(checked buyer_id={buyer_id} and campaign_id only)"
        )
        return None


@dataclass
class UpdateImportVideoInput:
    """Input for update_import_with_video activity."""

    import_id: str
    video_url: str
    status: str = "ready"


@activity.defn
async def update_import_with_video(input: UpdateImportVideoInput) -> ImportQueueRecord:
    """
    Update historical import with video URL and change status.

    Args:
        input: UpdateImportVideoInput with import_id, video_url, status

    Returns:
        Updated ImportQueueRecord
    """
    activity.logger.info(
        f"Updating import with video: {input.import_id} -> {input.video_url}"
    )

    headers = _get_supabase_headers()
    base_url = _get_supabase_url()

    update_data = {
        "video_url": input.video_url,
        "status": input.status,
        "updated_at": datetime.utcnow().isoformat(),
    }

    async with httpx.AsyncClient() as client:
        response = await client.patch(
            f"{base_url}/historical_import_queue?id=eq.{input.import_id}",
            headers=headers,
            json=update_data,
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()

        if not data:
            raise ApplicationError(f"Import not found: {input.import_id}")

        activity.logger.info(f"Updated import with video: {input.import_id}")
        return ImportQueueRecord.from_dict(data[0])
