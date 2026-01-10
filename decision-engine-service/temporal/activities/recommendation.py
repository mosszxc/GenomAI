"""
Recommendation Activities

Temporal activities for daily recommendation generation and delivery.
Replaces n8n workflows:
- wgEdEqt2BA3P9JlA (Daily Recommendation Generator)
- QC8bmnAYdH5mkntG (Recommendation Delivery)
"""

import os
import uuid
from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass

from temporalio import activity
from temporalio.exceptions import ApplicationError
import httpx


SCHEMA = "genomai"
TELEGRAM_API_BASE = "https://api.telegram.org"


@dataclass
class BuyerInfo:
    """Buyer information for recommendation generation"""

    id: str
    telegram_id: str
    name: str
    geo: Optional[str] = None
    vertical: Optional[str] = None
    geos: Optional[List[str]] = None
    verticals: Optional[List[str]] = None


@dataclass
class RecommendationResult:
    """Result of recommendation generation"""

    recommendation_id: str
    buyer_id: str
    mode: str
    description: str
    avg_confidence: float
    components: dict


def _get_credentials():
    """Get Supabase credentials from environment"""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        raise ApplicationError("Supabase credentials not configured")

    return f"{supabase_url}/rest/v1", supabase_key


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


@activity.defn
async def get_active_buyers() -> List[dict]:
    """
    Get all active buyers for recommendation generation.

    Returns:
        List of active buyers with their telegram_id, geo, vertical
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    activity.logger.info("Fetching active buyers for recommendations")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{rest_url}/buyers"
            "?status=eq.active"
            "&select=id,telegram_id,name,geo,vertical,geos,verticals",
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()

    activity.logger.info(f"Found {len(data)} active buyers")
    return data


@activity.defn
async def generate_recommendation_for_buyer(
    buyer_id: str,
    geo: Optional[str] = None,
    vertical: Optional[str] = None,
) -> dict:
    """
    Generate a recommendation for a specific buyer.

    Calls the existing recommendation service internally.

    Args:
        buyer_id: Buyer UUID
        geo: Geographic context (optional)
        vertical: Vertical context (optional)

    Returns:
        Recommendation data including id, mode, description, components
    """
    rest_url, supabase_key = _get_credentials()
    _get_headers(supabase_key, for_write=True)
    api_key = os.getenv("API_KEY")
    api_url = os.getenv("API_URL", "http://localhost:10000")

    activity.logger.info(f"Generating recommendation for buyer {buyer_id}")

    # Call the recommendation API
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{api_url}/recommendations/generate",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "buyer_id": buyer_id,
                "geo": geo,
                "vertical": vertical,
            },
            timeout=30.0,
        )

        if response.status_code != 200:
            error_detail = response.text
            activity.logger.error(f"Failed to generate recommendation: {error_detail}")
            raise ApplicationError(
                f"Recommendation generation failed: {error_detail}",
                type="RECOMMENDATION_ERROR",
            )

        data = response.json()

        if not data.get("success"):
            raise ApplicationError(
                f"Recommendation failed: {data.get('error')}",
                type="RECOMMENDATION_ERROR",
            )

        result = data["data"]
        activity.logger.info(
            f"Generated recommendation {result['id']} for buyer {buyer_id} "
            f"(mode={result['mode']}, confidence={result['avg_confidence']:.2f})"
        )

        return result


@activity.defn
async def send_recommendation_to_telegram(
    recommendation_id: str,
    buyer_telegram_id: str,
    buyer_name: str,
    description: str,
    mode: str,
    avg_confidence: float,
    components: list,
) -> dict:
    """
    Send recommendation to buyer via Telegram.

    Args:
        recommendation_id: Recommendation UUID
        buyer_telegram_id: Telegram chat ID
        buyer_name: Buyer name for personalization
        description: Recommendation description
        mode: exploitation or exploration
        avg_confidence: Average confidence score
        components: List of recommended components

    Returns:
        dict with message_id, status, timestamp
    """
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        raise ApplicationError("TELEGRAM_BOT_TOKEN not configured")

    activity.logger.info(
        f"Sending recommendation {recommendation_id} to {buyer_name} (chat_id={buyer_telegram_id})"
    )

    # Format message
    message = _format_recommendation_message(
        recommendation_id=recommendation_id,
        buyer_name=buyer_name,
        description=description,
        mode=mode,
        avg_confidence=avg_confidence,
        components=components,
    )

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{TELEGRAM_API_BASE}/bot{bot_token}/sendMessage",
                json={
                    "chat_id": buyer_telegram_id,
                    "text": message,
                    "parse_mode": "HTML",
                },
                timeout=30.0,
            )

            data = response.json()

            if not data.get("ok"):
                error_desc = data.get("description", "Unknown Telegram error")
                activity.logger.error(f"Telegram API error: {error_desc}")
                raise ApplicationError(
                    f"Telegram API error: {error_desc}",
                    type="TELEGRAM_ERROR",
                )

            result = data.get("result", {})
            message_id = result.get("message_id")

            activity.logger.info(
                f"Recommendation sent successfully: message_id={message_id}"
            )

            return {
                "recommendation_id": recommendation_id,
                "message_id": message_id,
                "chat_id": buyer_telegram_id,
                "status": "delivered",
                "timestamp": datetime.utcnow().isoformat(),
            }

        except httpx.TimeoutException:
            raise ApplicationError(
                "Telegram API timeout",
                type="TELEGRAM_TIMEOUT",
            )
        except httpx.RequestError as e:
            raise ApplicationError(
                f"Telegram request error: {e}",
                type="TELEGRAM_REQUEST_ERROR",
            )


def _format_recommendation_message(
    recommendation_id: str,
    buyer_name: str,
    description: str,
    mode: str,
    avg_confidence: float,
    components: list,
) -> str:
    """Format recommendation for Telegram message."""

    # Short ID for display
    short_id = recommendation_id[:8].upper()

    # Mode emoji and text
    if mode == "exploration":
        mode_text = "новая комбинация"
        mode_emoji = "🧪"
    else:
        mode_text = "проверенная комбинация"
        mode_emoji = "✅"

    # Format components
    component_lines = []
    for comp in components[:5]:  # Top 5
        comp_type = comp.get("type", "")
        comp_value = comp.get("value", "")
        confidence = comp.get("confidence", 0)
        confidence_pct = int(confidence * 100)

        # Component type emoji
        type_emoji = {
            "hook_mechanism": "🪝",
            "angle_type": "📐",
            "proof_type": "📋",
            "emotion_primary": "💭",
            "source_type": "📦",
            "message_structure": "📝",
        }.get(comp_type, "•")

        readable_type = comp_type.replace("_", " ").title()
        component_lines.append(
            f"{type_emoji} {readable_type}: {comp_value} ({confidence_pct}%)"
        )

    components_text = "\n".join(component_lines)

    # Average confidence
    avg_pct = int(avg_confidence * 100)

    lines = [
        f"📋 <b>Рекомендация #{short_id}</b>",
        "",
        f"👋 {buyer_name}, вот что попробовать сегодня:",
        "",
        "🎯 <b>Компоненты:</b>",
        components_text,
        "",
        f"{mode_emoji} Тип: {mode_text}",
        f"📊 Средняя уверенность: {avg_pct}%",
        "",
        "━━━━━━━━━━━━━━━",
        "После создания креатива загрузи видео",
        f"и укажи <code>R-{short_id}</code>",
    ]

    return "\n".join(lines)


@activity.defn
async def update_recommendation_delivery(
    recommendation_id: str,
    message_id: Optional[int] = None,
    status: str = "delivered",
) -> None:
    """
    Update recommendation with delivery info.

    Args:
        recommendation_id: Recommendation UUID
        message_id: Telegram message ID
        status: Delivery status
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)

    update_data = {
        "status": status,
    }

    if message_id:
        update_data["telegram_message_id"] = str(message_id)

    if status == "delivered":
        update_data["accepted_at"] = datetime.utcnow().isoformat()

    async with httpx.AsyncClient() as client:
        response = await client.patch(
            f"{rest_url}/recommendations?id=eq.{recommendation_id}",
            headers=headers,
            json=update_data,
        )
        response.raise_for_status()

    activity.logger.info(f"Updated recommendation {recommendation_id}: status={status}")


@activity.defn
async def emit_recommendation_event(
    recommendation_id: str,
    buyer_id: str,
    event_type: str,
    error: Optional[str] = None,
) -> dict:
    """
    Emit recommendation event to event log.

    Args:
        recommendation_id: Recommendation UUID
        buyer_id: Buyer UUID
        event_type: Event type (RecommendationGenerated, RecommendationDelivered, etc.)
        error: Optional error message

    Returns:
        Created event dict
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)

    event = {
        "id": str(uuid.uuid4()),
        "event_type": event_type,
        "entity_type": "recommendation",
        "entity_id": recommendation_id,
        "payload": {
            "recommendation_id": recommendation_id,
            "buyer_id": buyer_id,
            "error": error,
        },
        "occurred_at": datetime.utcnow().isoformat(),
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{rest_url}/event_log",
            headers=headers,
            json=event,
        )
        response.raise_for_status()
        data = response.json()

        return data[0] if data else event


@activity.defn
async def get_recommendation_by_id(recommendation_id: str) -> Optional[dict]:
    """
    Get recommendation by ID.

    Args:
        recommendation_id: Recommendation UUID

    Returns:
        Recommendation data or None
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{rest_url}/recommendations?id=eq.{recommendation_id}",
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()

        return data[0] if data else None


@activity.defn
async def check_existing_daily_recommendation(buyer_id: str) -> Optional[str]:
    """
    Check if buyer already has a recommendation today.

    Args:
        buyer_id: Buyer UUID

    Returns:
        Existing recommendation ID or None
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    today = datetime.utcnow().date().isoformat()

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{rest_url}/recommendations"
            f"?buyer_id=eq.{buyer_id}"
            f"&created_at=gte.{today}"
            "&select=id"
            "&limit=1",
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()

        if data:
            return data[0]["id"]
        return None
