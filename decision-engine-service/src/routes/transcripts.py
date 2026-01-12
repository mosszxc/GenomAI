"""
Transcripts Webhook Router

Receives status updates from Supabase pg_net trigger when transcript
processing status changes (Convert, Transcribe, Translate).
"""

from fastapi import APIRouter, Request, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class TranscriptStatusPayload(BaseModel):
    """Payload from Supabase pg_net trigger."""

    id: int
    creative_id: str
    ConvertStatus: Optional[str] = None
    TranscribeStatus: Optional[str] = None
    TranslateStatus: Optional[str] = None
    changed_at: Optional[str] = None


@router.post("/webhook/transcript-status")
async def transcript_status_webhook(
    request: Request, background_tasks: BackgroundTasks
):
    """
    Receive transcript status updates from Supabase pg_net trigger.

    Called when ConvertStatus, TranscribeStatus, or TranslateStatus
    changes in genomai.transcripts table.
    """
    try:
        payload = await request.json()
        logger.info(
            f"Transcript status update: id={payload.get('id')}, "
            f"ConvertStatus={payload.get('ConvertStatus')}, "
            f"TranscribeStatus={payload.get('TranscribeStatus')}, "
            f"TranslateStatus={payload.get('TranslateStatus')}"
        )

        return {"ok": True, "received": payload.get("id")}

    except Exception as e:
        logger.error(f"Transcript webhook error: {e}")
        return {"ok": True, "error": str(e)}
