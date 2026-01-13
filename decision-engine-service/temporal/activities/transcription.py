"""
Transcription Activity

Temporal activity for AssemblyAI transcription with heartbeats for long-running operations.
AssemblyAI transcription typically takes 2-10 minutes, so heartbeats are essential
for crash recovery and cancellation support.

Supports two transcription paths:
1. Direct AssemblyAI: For public URLs (non-Google Drive)
2. n8n Webhook: For Google Drive URLs (requires OAuth in n8n)
"""

import os
import re
import time
from typing import Optional
from temporalio import activity
from temporalio.exceptions import ApplicationError

from temporal.tracing import get_activity_logger
from src.core.http_client import get_http_client

# Polling interval for transcription status (seconds)
POLL_INTERVAL = 30

# n8n webhook for video transcription (MP4→MP3 conversion + AssemblyAI)
N8N_WEBHOOK_URL = os.getenv(
    "N8N_TRANSCRIBE_WEBHOOK",
    "https://aideportment.nl.tuna.am/webhook/MP3MP4",
)

# Maximum wait time before timeout (seconds) - 15 minutes
MAX_WAIT_TIME = 900


def is_google_drive_url(url: str) -> bool:
    """Check if URL is a Google Drive URL."""
    return "drive.google.com" in url or "docs.google.com" in url


def extract_gdrive_file_id(url: str) -> Optional[str]:
    """
    Extract Google Drive file ID from various URL formats.

    Supports:
    - https://drive.google.com/file/d/{FILE_ID}/view...
    - https://drive.google.com/uc?export=download&id={FILE_ID}
    - https://drive.google.com/open?id={FILE_ID}

    Returns:
        File ID or None if not a Google Drive URL
    """
    # Pattern 1: /file/d/{ID}/
    match = re.search(r"/file/d/([a-zA-Z0-9_-]+)", url)
    if match:
        return match.group(1)

    # Pattern 2: id={ID} in query string
    match = re.search(r"[?&]id=([a-zA-Z0-9_-]+)", url)
    if match:
        return match.group(1)

    return None


def convert_to_direct_url(url: str) -> str:
    """
    Convert cloud storage URLs to direct download URLs.

    Supports:
    - Google Drive: /file/d/{ID}/view -> /uc?export=download&id={ID}
    - Dropbox: ?dl=0 -> ?dl=1

    Args:
        url: Original URL

    Returns:
        Direct download URL (or original if not a known cloud storage URL)
    """
    # Google Drive pattern: https://drive.google.com/file/d/{FILE_ID}/view...
    gdrive_pattern = r"https?://drive\.google\.com/file/d/([^/]+)"
    gdrive_match = re.search(gdrive_pattern, url)
    if gdrive_match:
        file_id = gdrive_match.group(1)
        return f"https://drive.google.com/uc?export=download&id={file_id}"

    # Dropbox pattern: change ?dl=0 to ?dl=1
    if "dropbox.com" in url:
        if "?dl=0" in url:
            return url.replace("?dl=0", "?dl=1")
        elif "dl=0" not in url and "dl=1" not in url:
            separator = "&" if "?" in url else "?"
            return f"{url}{separator}dl=1"

    # Return original if not a known cloud storage URL
    return url


async def transcribe_via_n8n(
    video_url: str,
    creative_id: str,
) -> dict:
    """
    Transcribe video via n8n webhook (MP4→MP3 conversion + AssemblyAI).

    n8n workflow handles:
    1. Convert MP4 to MP3
    2. Upload to AssemblyAI
    3. Start transcription
    4. Poll for result
    5. Update genomai.transcripts table

    Args:
        video_url: Full video URL (Google Drive or other)
        creative_id: Creative UUID for transcript linking

    Returns:
        dict with transcript_id, text, status
    """
    log = get_activity_logger(creative_id=creative_id)

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        raise ApplicationError("SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not configured")

    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json",
        "Content-Profile": "genomai",
        "Accept-Profile": "genomai",
        "Prefer": "return=representation",
    }

    # Step 1: Create transcript record in DB
    log.info("Creating transcript record")

    client = get_http_client()
    # Extract Google Drive file ID for VideoID field
    video_id = extract_gdrive_file_id(video_url)

    # Insert transcript record with VideoID for pg_cron worker
    insert_resp = await client.post(
        f"{supabase_url}/rest/v1/transcripts",
        headers=headers,
        json={
            "creative_id": creative_id,
            "Name": f"transcript_{creative_id[:8]}",  # Required by pg_cron
            "VideoID": video_id,  # Google Drive file ID for Convert stage
            "ConvertStatus": "queued",  # Triggers pg_cron worker
            "Status": "queued",
        },
    )

    if insert_resp.status_code not in (200, 201):
        raise ApplicationError(f"Failed to create transcript: {insert_resp.text}")

    # Get the created record ID
    created = insert_resp.json()
    transcript_db_id = created[0]["id"] if isinstance(created, list) else created.get("id")

    if not transcript_db_id:
        # Fetch the latest transcript for this creative
        get_resp = await client.get(
            f"{supabase_url}/rest/v1/transcripts",
            headers=headers,
            params={
                "creative_id": f"eq.{creative_id}",
                "order": "created_at.desc",
                "limit": "1",
            },
        )
        if get_resp.status_code == 200:
            records = get_resp.json()
            if records:
                transcript_db_id = records[0]["id"]

    log.info("Created transcript record", transcript_db_id=transcript_db_id)

    # Step 2: Poll transcripts table for result
    # pg_cron worker will pick up the record and call webhooks:
    # ConvertStatus=queued → MP3MP4 webhook → AudioID
    # TranscribeStatus=queued → AudioTranscribe webhook → transcript_text
    log.info(
        "Waiting for pg_cron worker to process transcript",
        transcript_db_id=transcript_db_id,
    )

    elapsed = 0

    while elapsed < MAX_WAIT_TIME:
        # Check cancellation
        if activity.is_cancelled():
            raise ApplicationError("Transcription cancelled", type="CANCELLED")

        # Send heartbeat
        activity.heartbeat(
            {
                "transcript_db_id": transcript_db_id,
                "elapsed_seconds": elapsed,
                "method": "n8n",
            }
        )

        # Check transcript status
        client = get_http_client()
        check_resp = await client.get(
            f"{supabase_url}/rest/v1/transcripts",
            headers=headers,
            params={
                "id": f"eq.{transcript_db_id}",
                "select": "id,transcript_text,TranscribeStatus,assemblyai_transcript_id",
            },
        )

        if check_resp.status_code == 200:
            records = check_resp.json()
            if records:
                record = records[0]
                status = record.get("TranscribeStatus", "")

                if status == "finish":
                    log.info("Transcription completed via n8n")

                    # Update Status to finish to unblock pg_cron queue
                    # n8n webhook only sets TranscribeStatus, not Status
                    await client.patch(
                        f"{supabase_url}/rest/v1/transcripts",
                        headers=headers,
                        params={"id": f"eq.{transcript_db_id}"},
                        json={"Status": "finish"},
                    )

                    return {
                        "transcript_id": record.get(
                            "assemblyai_transcript_id", str(transcript_db_id)
                        ),
                        "text": record.get("transcript_text", ""),
                        "status": "completed",
                        "words": len(record.get("transcript_text", "").split()),
                    }

                if status == "error":
                    raise ApplicationError(
                        f"n8n transcription failed: {record.get('transcript_text', 'Unknown error')}",
                        type="TRANSCRIPTION_ERROR",
                    )

        log.info("Waiting for n8n transcription", elapsed_seconds=elapsed)
        time.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL

    raise ApplicationError(
        f"n8n transcription timeout after {MAX_WAIT_TIME}s",
        type="TIMEOUT",
    )


@activity.defn
async def transcribe_audio(
    audio_url: str,
    language_code: Optional[str] = None,
    creative_id: Optional[str] = None,
) -> dict:
    """
    Transcribe audio/video using AssemblyAI.

    This activity handles long-running transcription jobs (2-10 minutes)
    with periodic heartbeats for crash recovery.

    For Google Drive URLs, uses n8n webhook which has OAuth access.
    For other URLs, uses direct AssemblyAI submission.

    Args:
        audio_url: URL to audio/video file
        language_code: Optional language code (e.g., "en", "ru")
        creative_id: Creative UUID (required for Google Drive URLs)

    Returns:
        dict with transcript_id, text, and status

    Raises:
        ApplicationError: If transcription fails or is cancelled
    """
    log = get_activity_logger(creative_id=creative_id, audio_url=audio_url)

    # Check if Google Drive URL - use n8n path (MP4→MP3 conversion)
    if is_google_drive_url(audio_url):
        if not creative_id:
            raise ApplicationError(
                "creative_id is required for Google Drive transcription",
                type="MISSING_PARAM",
            )

        log.info("Using n8n path for video URL")
        return await transcribe_via_n8n(audio_url, creative_id)

    # Direct AssemblyAI path for non-Google Drive URLs
    import assemblyai as aai

    api_key = os.getenv("ASSEMBLYAI_API_KEY")
    if not api_key:
        raise ApplicationError("ASSEMBLYAI_API_KEY not configured")

    aai.settings.api_key = api_key

    # Convert cloud storage URLs to direct download URLs
    original_url = audio_url
    audio_url = convert_to_direct_url(audio_url)
    if audio_url != original_url:
        log.info("Converted URL for direct download", original_url=original_url)

    log.info("Starting direct transcription")

    # Configure transcription
    config = aai.TranscriptionConfig(
        language_code=language_code,
    )

    transcriber = aai.Transcriber(config=config)

    # Submit job without waiting (async)
    transcript = transcriber.submit(audio_url)
    transcript_id = transcript.id

    log.info("Submitted transcription job", transcript_id=transcript_id)

    # Send initial heartbeat with transcript ID for recovery
    activity.heartbeat({"transcript_id": transcript_id, "status": "submitted"})

    # Poll for completion with heartbeats
    elapsed = 0
    while elapsed < MAX_WAIT_TIME:
        # Check for cancellation
        if activity.is_cancelled():
            log.warning("Transcription cancelled", transcript_id=transcript_id)
            raise ApplicationError(
                f"Transcription cancelled: {transcript_id}",
                type="CANCELLED",
            )

        # Check status
        transcript = aai.Transcript.get_by_id(transcript_id)

        if transcript.status == aai.TranscriptStatus.completed:
            log.info(
                "Transcription completed",
                transcript_id=transcript_id,
                words=len(transcript.text.split()) if transcript.text else 0,
            )
            return {
                "transcript_id": transcript_id,
                "text": transcript.text,
                "status": "completed",
                "words": len(transcript.text.split()) if transcript.text else 0,
            }

        if transcript.status == aai.TranscriptStatus.error:
            error_msg = transcript.error or "Unknown transcription error"
            log.error("Transcription failed", error=error_msg, transcript_id=transcript_id)
            raise ApplicationError(
                f"Transcription failed: {error_msg}",
                type="TRANSCRIPTION_ERROR",
            )

        # Send heartbeat with current status
        activity.heartbeat(
            {
                "transcript_id": transcript_id,
                "status": str(transcript.status),
                "elapsed_seconds": elapsed,
            }
        )

        log.info(
            "Transcription in progress",
            transcript_id=transcript_id,
            status=str(transcript.status),
            elapsed_seconds=elapsed,
        )

        # Wait before next poll
        time.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL

    # Timeout
    raise ApplicationError(
        f"Transcription timeout after {MAX_WAIT_TIME}s: {transcript_id}",
        type="TIMEOUT",
    )


@activity.defn
async def get_transcript(transcript_id: str) -> dict:
    """
    Get existing transcript by ID.

    Useful for recovery scenarios where transcript was already submitted.

    Args:
        transcript_id: AssemblyAI transcript ID

    Returns:
        dict with transcript_id, text, and status
    """
    import assemblyai as aai

    api_key = os.getenv("ASSEMBLYAI_API_KEY")
    if not api_key:
        raise ApplicationError("ASSEMBLYAI_API_KEY not configured")

    aai.settings.api_key = api_key

    transcript = aai.Transcript.get_by_id(transcript_id)

    if transcript.status == aai.TranscriptStatus.error:
        raise ApplicationError(
            f"Transcript error: {transcript.error}",
            type="TRANSCRIPTION_ERROR",
        )

    return {
        "transcript_id": transcript_id,
        "text": transcript.text if transcript.status == aai.TranscriptStatus.completed else None,
        "status": str(transcript.status),
    }
