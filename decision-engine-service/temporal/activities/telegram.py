"""
Telegram Activities

Temporal activities for Telegram-related operations.
After bot refactoring (#751), delivery activities removed.
Remaining activities support buyer lookups and event logging.
"""

import os
import uuid
from datetime import datetime
from typing import Any, List, Optional, cast

from temporalio import activity
from temporalio.exceptions import ApplicationError

from src.core.http_client import get_http_client


@activity.defn
async def get_buyer_chat_id(buyer_id: str) -> Optional[str]:
    """
    Get Telegram chat ID for a buyer.

    Args:
        buyer_id: Buyer UUID

    Returns:
        Telegram chat ID or None if not found
    """
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        raise ApplicationError("Supabase credentials not configured")

    rest_url = f"{supabase_url}/rest/v1"
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Accept-Profile": "genomai",
    }

    client = get_http_client()
    response = await client.get(
        f"{rest_url}/buyers?id=eq.{buyer_id}&select=telegram_id",
        headers=headers,
    )
    response.raise_for_status()
    data = cast(List[dict[str, Any]], response.json())

    if not data:
        return None

    return cast(Optional[str], data[0].get("telegram_id"))


@activity.defn
async def update_hypothesis_delivery_status(
    hypothesis_id: str,
    status: str,
    message_id: Optional[int] = None,
    error: Optional[str] = None,
) -> None:
    """
    Update hypothesis delivery status in Supabase.

    Args:
        hypothesis_id: Hypothesis UUID
        status: Delivery status (delivered/failed)
        message_id: Telegram message ID if delivered
        error: Error message if failed
    """
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        raise ApplicationError("Supabase credentials not configured")

    rest_url = f"{supabase_url}/rest/v1"
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Accept-Profile": "genomai",
        "Content-Profile": "genomai",
        "Content-Type": "application/json",
    }

    update_data = {
        "delivery_status": status,
        "delivered_at": datetime.utcnow().isoformat() if status == "delivered" else None,
    }

    if message_id:
        update_data["telegram_message_id"] = str(message_id)

    if error:
        update_data["delivery_error"] = error

    client = get_http_client()
    await client.patch(
        f"{rest_url}/hypotheses?id=eq.{hypothesis_id}",
        headers=headers,
        json=update_data,
    )

    activity.logger.info(f"Updated hypothesis delivery status: {hypothesis_id} -> {status}")


@activity.defn
async def emit_delivery_event(
    hypothesis_id: str,
    idea_id: str,
    status: str,
    error: Optional[str] = None,
) -> dict:
    """
    Emit delivery event to event log.

    Args:
        hypothesis_id: Hypothesis UUID
        idea_id: Idea UUID
        status: Delivery status
        error: Optional error message

    Returns:
        Created event dict
    """
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        raise ApplicationError("Supabase credentials not configured")

    rest_url = f"{supabase_url}/rest/v1"
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Accept-Profile": "genomai",
        "Content-Profile": "genomai",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

    event_type = "HypothesisDelivered" if status == "delivered" else "DeliveryFailed"

    event = {
        "id": str(uuid.uuid4()),
        "event_type": event_type,
        "entity_type": "hypothesis",
        "entity_id": hypothesis_id,
        "payload": {
            "hypothesis_id": hypothesis_id,
            "idea_id": idea_id,
            "status": status,
            "error": error,
        },
        "occurred_at": datetime.utcnow().isoformat(),
    }

    client = get_http_client()
    response = await client.post(
        f"{rest_url}/event_log",
        headers=headers,
        json=event,
    )
    response.raise_for_status()
    data = response.json()

    return data[0] if data else event
