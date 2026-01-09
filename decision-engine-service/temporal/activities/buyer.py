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
    base_url = _get_supabase_url()

    queue_entry = {
        "id": str(uuid.uuid4()),
        "buyer_id": input.buyer_id,
        "campaign_id": input.campaign_id,
        "video_url": input.video_url,
        "keitaro_source": input.keitaro_source,
        "metrics": input.metrics,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{base_url}/historical_import_queue",
            headers=headers,
            json=queue_entry,
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()

        entry_id = data[0]["id"] if data else queue_entry["id"]
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
