"""
Transcription Activity

Temporal activity for AssemblyAI transcription with heartbeats for long-running operations.
AssemblyAI transcription typically takes 2-10 minutes, so heartbeats are essential
for crash recovery and cancellation support.
"""

import os
import re
import time
from typing import Optional
from temporalio import activity
from temporalio.exceptions import ApplicationError

# Polling interval for transcription status (seconds)
POLL_INTERVAL = 30


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


# Maximum wait time before timeout (seconds) - 15 minutes
MAX_WAIT_TIME = 900


@activity.defn
async def transcribe_audio(
    audio_url: str,
    language_code: Optional[str] = None,
) -> dict:
    """
    Transcribe audio/video using AssemblyAI.

    This activity handles long-running transcription jobs (2-10 minutes)
    with periodic heartbeats for crash recovery.

    Args:
        audio_url: URL to audio/video file (must be publicly accessible)
        language_code: Optional language code (e.g., "en", "ru")

    Returns:
        dict with transcript_id, text, and status

    Raises:
        ApplicationError: If transcription fails or is cancelled
    """
    import assemblyai as aai

    api_key = os.getenv("ASSEMBLYAI_API_KEY")
    if not api_key:
        raise ApplicationError("ASSEMBLYAI_API_KEY not configured")

    aai.settings.api_key = api_key

    # Convert cloud storage URLs to direct download URLs
    original_url = audio_url
    audio_url = convert_to_direct_url(audio_url)
    if audio_url != original_url:
        activity.logger.info(f"Converted URL: {original_url} -> {audio_url}")

    activity.logger.info(f"Starting transcription for: {audio_url}")

    # Configure transcription
    config = aai.TranscriptionConfig(
        language_code=language_code,
    )

    transcriber = aai.Transcriber(config=config)

    # Submit job without waiting (async)
    transcript = transcriber.submit(audio_url)
    transcript_id = transcript.id

    activity.logger.info(f"Submitted transcription job: {transcript_id}")

    # Send initial heartbeat with transcript ID for recovery
    activity.heartbeat({"transcript_id": transcript_id, "status": "submitted"})

    # Poll for completion with heartbeats
    elapsed = 0
    while elapsed < MAX_WAIT_TIME:
        # Check for cancellation
        if activity.is_cancelled():
            activity.logger.warning(f"Transcription cancelled: {transcript_id}")
            raise ApplicationError(
                f"Transcription cancelled: {transcript_id}",
                type="CANCELLED",
            )

        # Check status
        transcript = aai.Transcript.get_by_id(transcript_id)

        if transcript.status == aai.TranscriptStatus.completed:
            activity.logger.info(f"Transcription completed: {transcript_id}")
            return {
                "transcript_id": transcript_id,
                "text": transcript.text,
                "status": "completed",
                "words": len(transcript.text.split()) if transcript.text else 0,
            }

        if transcript.status == aai.TranscriptStatus.error:
            error_msg = transcript.error or "Unknown transcription error"
            activity.logger.error(f"Transcription failed: {error_msg}")
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

        activity.logger.info(
            f"Transcription in progress: {transcript_id}, "
            f"status={transcript.status}, elapsed={elapsed}s"
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
        "text": transcript.text
        if transcript.status == aai.TranscriptStatus.completed
        else None,
        "status": str(transcript.status),
    }
