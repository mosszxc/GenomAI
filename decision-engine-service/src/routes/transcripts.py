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
    convert_status: Optional[str] = None
    transcribe_status: Optional[str] = None
    translate_status: Optional[str] = None
    changed_at: Optional[str] = None


@router.post("/webhook/transcript-status")
async def transcript_status_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Receive transcript status updates from Supabase pg_net trigger.

    Called when convert_status, transcribe_status, or translate_status
    changes in genomai.transcripts table.
    """
    try:
        payload = await request.json()
        logger.info(
            f"Transcript status update: id={payload.get('id')}, "
            f"convert_status={payload.get('convert_status')}, "
            f"transcribe_status={payload.get('transcribe_status')}, "
            f"translate_status={payload.get('translate_status')}"
        )

        return {"ok": True, "received": payload.get("id")}

    except Exception as e:
        logger.error(f"Transcript webhook error: {e}")
        return {"ok": True, "error": str(e)}
