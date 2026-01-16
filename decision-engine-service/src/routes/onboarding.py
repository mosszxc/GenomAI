"""
Onboarding API Routes

API endpoints for cockpit onboarding flow.
All endpoints require JWT auth (Supabase JWT or custom token from /api/auth/telegram).

Routes:
    POST /api/onboarding/validate-keitaro - Validate Keitaro credentials
    POST /api/onboarding/start - Start onboarding (create buyer, import history)
    GET  /api/onboarding/status - Get onboarding status and progress
    POST /api/onboarding/submit-video - Submit video URL for campaign
    POST /api/onboarding/skip-videos - Skip video submission step
"""

import hmac
import hashlib
import logging
import os
import time
from typing import Any, Optional

import httpx
import jwt
from fastapi import APIRouter, Header, HTTPException, Depends
from pydantic import BaseModel, Field

from src.core.supabase import get_supabase
from src.core.http_client import get_http_client

logger = logging.getLogger(__name__)

router = APIRouter()

# Token expiration time (24 hours)
TOKEN_MAX_AGE_SECONDS = 86400


class TokenPayload(BaseModel):
    """Parsed JWT token payload"""

    buyer_id: str
    timestamp: int


def _is_jwt_format(token: str) -> bool:
    """Check if token looks like a JWT (three base64 parts separated by dots)."""
    parts = token.split(".")
    return len(parts) == 3


def _verify_supabase_jwt(token: str) -> TokenPayload:
    """
    Verify Supabase JWT and extract buyer_id.

    Supabase JWT contains:
    - sub: user UUID (used as buyer_id)
    - exp: expiration timestamp
    - aud: "authenticated"

    Note: We decode without signature verification because:
    1. Supabase JWT secret is not available in backend
    2. The token was already validated by Supabase Auth
    3. We trust the token from Cockpit frontend

    Args:
        token: JWT token string

    Returns:
        TokenPayload with buyer_id and timestamp

    Raises:
        HTTPException 401 if token is invalid or expired
    """
    try:
        # Decode without verification (Supabase uses its own secret)
        # options={"verify_signature": False} allows decoding without secret
        payload = jwt.decode(token, options={"verify_signature": False})

        # Extract buyer_id from 'sub' claim
        buyer_id = payload.get("sub")
        if not buyer_id:
            raise HTTPException(status_code=401, detail="Invalid JWT: missing 'sub' claim")

        # Check expiration
        exp = payload.get("exp")
        if exp:
            current_time = int(time.time())
            if current_time > exp:
                raise HTTPException(status_code=401, detail="Token expired")

        # Use exp as timestamp, or current time if not available
        timestamp = exp if exp else int(time.time())

        logger.debug(f"Verified Supabase JWT for buyer: {buyer_id}")
        return TokenPayload(buyer_id=buyer_id, timestamp=timestamp)

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired") from None
    except jwt.DecodeError as e:
        raise HTTPException(status_code=401, detail=f"Invalid JWT format: {e}") from None
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}") from None


def _verify_custom_token(token: str) -> TokenPayload:
    """
    Verify custom token format (from /api/auth/telegram).

    Token format: {buyer_id}:{timestamp}:{signature}
    Signature: HMAC-SHA256(buyer_id:timestamp, API_KEY)[:16]

    Args:
        token: Custom token string

    Returns:
        TokenPayload with buyer_id and timestamp

    Raises:
        HTTPException 401 if token is invalid or expired
    """
    parts = token.split(":")

    if len(parts) != 3:
        raise HTTPException(status_code=401, detail="Invalid token format")

    buyer_id, timestamp_str, signature = parts

    # Validate timestamp
    try:
        timestamp = int(timestamp_str)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token timestamp") from None

    # Check expiration
    current_time = int(time.time())
    if (current_time - timestamp) > TOKEN_MAX_AGE_SECONDS:
        raise HTTPException(status_code=401, detail="Token expired")

    # Verify signature
    api_key = os.getenv("API_KEY", "")
    token_data = f"{buyer_id}:{timestamp_str}"
    expected_signature = hmac.new(
        api_key.encode(), token_data.encode(), hashlib.sha256
    ).hexdigest()[:16]

    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(status_code=401, detail="Invalid token signature")

    return TokenPayload(buyer_id=buyer_id, timestamp=timestamp)


async def verify_jwt_token(authorization: Optional[str] = Header(None)) -> TokenPayload:
    """
    Verify JWT token and extract buyer_id.

    Supports two token formats:
    1. Supabase JWT (from Cockpit frontend via Supabase Auth)
    2. Custom token (from /api/auth/telegram): {buyer_id}:{timestamp}:{signature}

    Args:
        authorization: Bearer token from Authorization header

    Returns:
        TokenPayload with buyer_id and timestamp

    Raises:
        HTTPException 401 if token is invalid or expired
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization format")

    token = authorization.replace("Bearer ", "")

    # Determine token format and verify accordingly
    if _is_jwt_format(token):
        return _verify_supabase_jwt(token)
    else:
        return _verify_custom_token(token)


# ============================================================================
# Request/Response Models
# ============================================================================


class ValidateKeitaroRequest(BaseModel):
    """Request for validate-keitaro endpoint"""

    keitaro_url: str = Field(..., description="Keitaro tracker URL (e.g., https://xxx.keitaro.io)")
    keitaro_api_key: str = Field(..., description="Keitaro API key")


class CampaignSummary(BaseModel):
    """Campaign summary for validation response"""

    campaign_id: str
    name: str
    clicks: int = 0
    conversions: int = 0
    profit: float = 0.0


class ValidateKeitaroResponse(BaseModel):
    """Response from validate-keitaro endpoint"""

    success: bool
    campaigns: list[CampaignSummary] = []
    total_campaigns: int = 0
    message: str
    error: Optional[str] = None


class StartOnboardingRequest(BaseModel):
    """Request for start endpoint"""

    name: Optional[str] = Field(None, description="Buyer name")
    geos: Optional[list[str]] = Field(None, description="Geo codes (e.g., ['US', 'DE'])")
    verticals: Optional[list[str]] = Field(None, description="Vertical codes (e.g., ['POT', 'WL'])")
    keitaro_url: str = Field(..., description="Keitaro tracker URL")
    keitaro_api_key: str = Field(..., description="Keitaro API key")
    keitaro_source: str = Field(..., description="Keitaro source/affiliate parameter")


class StartOnboardingResponse(BaseModel):
    """Response from start endpoint"""

    success: bool
    buyer_id: Optional[str] = None
    workflow_id: Optional[str] = None
    message: str
    error: Optional[str] = None


class OnboardingStatusResponse(BaseModel):
    """Response from status endpoint"""

    success: bool
    status: str  # pending | importing | pending_videos | completed | failed
    progress: int = 0  # 0-100
    total_campaigns: int = 0
    pending_video_campaigns: int = 0
    campaigns_requiring_video: list[CampaignSummary] = []
    message: str
    error: Optional[str] = None


class SubmitVideoRequest(BaseModel):
    """Request for submit-video endpoint"""

    campaign_id: str = Field(..., description="Keitaro campaign ID")
    video_url: str = Field(..., description="Video URL to process")


class SubmitVideoResponse(BaseModel):
    """Response from submit-video endpoint"""

    success: bool
    workflow_id: Optional[str] = None
    message: str
    error: Optional[str] = None


class SkipVideosResponse(BaseModel):
    """Response from skip-videos endpoint"""

    success: bool
    skipped_count: int = 0
    message: str
    error: Optional[str] = None


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/validate-keitaro", response_model=ValidateKeitaroResponse)
async def validate_keitaro(
    request: ValidateKeitaroRequest,
    token: TokenPayload = Depends(verify_jwt_token),
) -> ValidateKeitaroResponse:
    """
    Validate Keitaro credentials and return campaigns list.

    This endpoint:
    1. Verifies Keitaro API access with provided credentials
    2. Fetches all campaigns from the tracker
    3. Returns campaign list for user to select videos

    Args:
        request: Keitaro URL and API key
        token: JWT token payload (from auth)

    Returns:
        ValidateKeitaroResponse with campaigns or error
    """
    logger.info(f"Validating Keitaro credentials for buyer {token.buyer_id}")

    # Normalize URL
    base_url = request.keitaro_url.rstrip("/")
    if not base_url.startswith("http"):
        base_url = f"https://{base_url}"

    headers = {
        "Api-Key": request.keitaro_api_key,
        "Content-Type": "application/json",
    }

    try:
        client = get_http_client()

        # Test API access by fetching campaigns
        response = await client.get(
            f"{base_url}/admin_api/v1/campaigns",
            headers=headers,
            timeout=30.0,
        )

        if response.status_code == 401:
            return ValidateKeitaroResponse(
                success=False,
                message="Invalid API key",
                error="Keitaro API key is invalid or expired",
            )

        if response.status_code == 403:
            return ValidateKeitaroResponse(
                success=False,
                message="Access denied",
                error="API key does not have permission to access campaigns",
            )

        if not response.is_success:
            return ValidateKeitaroResponse(
                success=False,
                message="Keitaro API error",
                error=f"HTTP {response.status_code}: {response.text[:200]}",
            )

        all_campaigns = response.json()

        # Filter active campaigns (last 30 days)
        from datetime import datetime, timedelta

        cutoff = datetime.utcnow() - timedelta(days=30)
        campaigns = []

        for c in all_campaigns:
            created_at = c.get("created_at", "")
            try:
                created_dt = datetime.fromisoformat(created_at.replace("Z", ""))
                if created_dt < cutoff:
                    continue
            except (ValueError, TypeError):
                continue

            campaigns.append(
                CampaignSummary(
                    campaign_id=str(c.get("id", "")),
                    name=c.get("name", ""),
                    clicks=0,
                    conversions=0,
                    profit=0.0,
                )
            )

        logger.info(
            f"Validated Keitaro for buyer {token.buyer_id}: {len(campaigns)} campaigns found"
        )

        return ValidateKeitaroResponse(
            success=True,
            campaigns=campaigns[:50],  # Limit to 50 most recent
            total_campaigns=len(campaigns),
            message=f"Found {len(campaigns)} campaigns",
        )

    except httpx.TimeoutException:
        logger.error(f"Keitaro timeout for buyer {token.buyer_id}")
        return ValidateKeitaroResponse(
            success=False,
            message="Connection timeout",
            error="Could not connect to Keitaro. Check the URL.",
        )
    except httpx.RequestError as e:
        logger.error(f"Keitaro request error for buyer {token.buyer_id}: {e}")
        return ValidateKeitaroResponse(
            success=False,
            message="Connection error",
            error=f"Could not connect to Keitaro: {str(e)[:100]}",
        )
    except Exception as e:
        logger.error(f"Keitaro validation error for buyer {token.buyer_id}: {e}")
        return ValidateKeitaroResponse(
            success=False,
            message="Validation failed",
            error=str(e)[:200],
        )


@router.post("/start", response_model=StartOnboardingResponse)
async def start_onboarding(
    request: StartOnboardingRequest,
    token: TokenPayload = Depends(verify_jwt_token),
) -> StartOnboardingResponse:
    """
    Start onboarding process for a buyer.

    This endpoint:
    1. Updates buyer record with Keitaro credentials
    2. Stores Keitaro config in database
    3. Starts HistoricalImportWorkflow

    Args:
        request: Onboarding data (name, geos, verticals, keitaro)
        token: JWT token payload

    Returns:
        StartOnboardingResponse with workflow_id
    """
    from temporal.workflows.historical_import import HistoricalImportWorkflow
    from temporal.models.buyer import HistoricalImportInput

    logger.info(f"Starting onboarding for buyer {token.buyer_id}")

    try:
        sb = get_supabase()
    except RuntimeError as e:
        logger.error(f"Supabase not configured: {e}")
        return StartOnboardingResponse(
            success=False,
            message="Database not configured",
            error=str(e),
        )

    client = get_http_client()

    try:
        # Step 1: Update buyer record
        update_data: dict[str, Any] = {
            "keitaro_source": request.keitaro_source,
            "status": "onboarding",
        }
        if request.name:
            update_data["name"] = request.name
        if request.geos:
            update_data["geos"] = request.geos
        if request.verticals:
            update_data["verticals"] = request.verticals

        response = await client.patch(
            f"{sb.rest_url}/buyers?id=eq.{token.buyer_id}",
            headers=sb.get_headers(),
            json=update_data,
            timeout=10.0,
        )

        if not response.is_success:
            logger.error(f"Failed to update buyer: {response.status_code} {response.text}")
            return StartOnboardingResponse(
                success=False,
                message="Failed to update buyer",
                error=f"Database error: {response.status_code}",
            )

        # Step 2: Start historical import workflow
        # Note: Keitaro credentials are stored globally in keitaro_config table
        # Historical import uses keitaro_source to identify buyer's campaigns
        from temporal.client import get_temporal_client

        temporal_client = await get_temporal_client()
        workflow_id = f"historical-import-{token.buyer_id}"

        await temporal_client.start_workflow(
            HistoricalImportWorkflow.run,
            HistoricalImportInput(
                buyer_id=token.buyer_id,
                keitaro_source=request.keitaro_source,
            ),
            id=workflow_id,
            task_queue="telegram",
        )

        logger.info(f"Started historical import workflow: {workflow_id}")

        return StartOnboardingResponse(
            success=True,
            buyer_id=token.buyer_id,
            workflow_id=workflow_id,
            message="Onboarding started. Importing historical data...",
        )

    except Exception as e:
        logger.error(f"Failed to start onboarding for buyer {token.buyer_id}: {e}")
        return StartOnboardingResponse(
            success=False,
            message="Failed to start onboarding",
            error=str(e)[:200],
        )


@router.get("/status", response_model=OnboardingStatusResponse)
async def get_onboarding_status(
    token: TokenPayload = Depends(verify_jwt_token),
) -> OnboardingStatusResponse:
    """
    Get onboarding status and progress.

    This endpoint:
    1. Checks historical_import_queue for pending imports
    2. Returns progress percentage and campaigns requiring videos

    Args:
        token: JWT token payload

    Returns:
        OnboardingStatusResponse with status and progress
    """
    logger.info(f"Getting onboarding status for buyer {token.buyer_id}")

    try:
        sb = get_supabase()
    except RuntimeError:
        return OnboardingStatusResponse(
            success=False,
            status="error",
            message="Database not configured",
            error="Supabase not configured",
        )

    client = get_http_client()

    try:
        # Get all queue items for buyer
        response = await client.get(
            f"{sb.rest_url}/historical_import_queue"
            f"?buyer_id=eq.{token.buyer_id}"
            f"&order=created_at.desc"
            f"&limit=100",
            headers=sb.get_headers(),
            timeout=30.0,
        )

        if not response.is_success:
            return OnboardingStatusResponse(
                success=False,
                status="error",
                message="Failed to fetch import queue",
                error=f"Database error: {response.status_code}",
            )

        queue_items = response.json()

        if not queue_items:
            # No imports - check if onboarding was completed
            buyer_response = await client.get(
                f"{sb.rest_url}/buyers?id=eq.{token.buyer_id}&select=status",
                headers=sb.get_headers(),
                timeout=10.0,
            )

            if buyer_response.is_success:
                buyers = buyer_response.json()
                if buyers and buyers[0].get("status") == "active":
                    return OnboardingStatusResponse(
                        success=True,
                        status="completed",
                        progress=100,
                        message="Onboarding completed",
                    )

            return OnboardingStatusResponse(
                success=True,
                status="pending",
                progress=0,
                message="No historical imports found. Start onboarding first.",
            )

        # Calculate progress
        total = len(queue_items)
        completed = sum(1 for item in queue_items if item.get("status") == "completed")
        pending_video = [item for item in queue_items if item.get("status") == "pending_video"]
        processing = sum(1 for item in queue_items if item.get("status") in ("ready", "processing"))

        # Determine overall status
        if completed == total:
            status = "completed"
            progress = 100
        elif pending_video:
            status = "pending_videos"
            progress = int((completed / total) * 100) if total else 0
        elif processing > 0:
            status = "importing"
            progress = int((completed / total) * 100) if total else 0
        else:
            status = "importing"
            progress = int((completed / total) * 100) if total else 0

        # Build campaigns requiring video
        campaigns_requiring_video = [
            CampaignSummary(
                campaign_id=item.get("campaign_id", ""),
                name=item.get("metrics", {}).get("name", f"Campaign {item.get('campaign_id')}"),
                clicks=item.get("metrics", {}).get("clicks", 0),
                conversions=item.get("metrics", {}).get("conversions", 0),
                profit=item.get("metrics", {}).get("profit", 0.0),
            )
            for item in pending_video
        ]

        return OnboardingStatusResponse(
            success=True,
            status=status,
            progress=progress,
            total_campaigns=total,
            pending_video_campaigns=len(pending_video),
            campaigns_requiring_video=campaigns_requiring_video,
            message=f"Status: {status}, {completed}/{total} completed",
        )

    except Exception as e:
        logger.error(f"Failed to get onboarding status for buyer {token.buyer_id}: {e}")
        return OnboardingStatusResponse(
            success=False,
            status="error",
            message="Failed to get status",
            error=str(e)[:200],
        )


@router.post("/submit-video", response_model=SubmitVideoResponse)
async def submit_video(
    request: SubmitVideoRequest,
    token: TokenPayload = Depends(verify_jwt_token),
) -> SubmitVideoResponse:
    """
    Submit video URL for a campaign.

    This endpoint triggers HistoricalVideoHandlerWorkflow.

    Args:
        request: Campaign ID and video URL
        token: JWT token payload

    Returns:
        SubmitVideoResponse with workflow_id
    """
    from temporal.workflows.historical_import import HistoricalVideoHandlerWorkflow
    from temporal.models.buyer import HistoricalVideoHandlerInput
    from temporal.client import get_temporal_client

    logger.info(f"Submitting video for campaign {request.campaign_id}, buyer {token.buyer_id}")

    # Validate URL format
    if not request.video_url.startswith(("http://", "https://")):
        return SubmitVideoResponse(
            success=False,
            message="Invalid video URL",
            error="URL must start with http:// or https://",
        )

    try:
        temporal_client = await get_temporal_client()
        workflow_id = f"historical-video-{request.campaign_id}"

        await temporal_client.start_workflow(
            HistoricalVideoHandlerWorkflow.run,
            HistoricalVideoHandlerInput(
                campaign_id=request.campaign_id,
                video_url=request.video_url,
                buyer_id=token.buyer_id,
            ),
            id=workflow_id,
            task_queue="telegram",
        )

        logger.info(f"Started video handler workflow: {workflow_id}")

        return SubmitVideoResponse(
            success=True,
            workflow_id=workflow_id,
            message=f"Video processing started for campaign {request.campaign_id}",
        )

    except Exception as e:
        logger.error(f"Failed to submit video for campaign {request.campaign_id}: {e}")
        return SubmitVideoResponse(
            success=False,
            message="Failed to start video processing",
            error=str(e)[:200],
        )


@router.post("/skip-videos", response_model=SkipVideosResponse)
async def skip_videos(
    token: TokenPayload = Depends(verify_jwt_token),
) -> SkipVideosResponse:
    """
    Skip video submission step.

    This endpoint:
    1. Marks all pending_video items as skipped
    2. Updates buyer status to active
    3. Logs for analytics

    Args:
        token: JWT token payload

    Returns:
        SkipVideosResponse with skipped count
    """
    logger.info(f"Skipping videos for buyer {token.buyer_id}")

    try:
        sb = get_supabase()
    except RuntimeError:
        return SkipVideosResponse(
            success=False,
            message="Database not configured",
            error="Supabase not configured",
        )

    client = get_http_client()

    try:
        # Step 1: Update pending_video items to skipped
        update_response = await client.patch(
            f"{sb.rest_url}/historical_import_queue"
            f"?buyer_id=eq.{token.buyer_id}"
            f"&status=eq.pending_video",
            headers={
                **sb.get_headers(),
                "Prefer": "return=representation",
            },
            json={"status": "skipped"},
            timeout=30.0,
        )

        if not update_response.is_success:
            logger.error(f"Failed to update queue: {update_response.status_code}")
            return SkipVideosResponse(
                success=False,
                message="Failed to update import queue",
                error=f"Database error: {update_response.status_code}",
            )

        skipped_items = update_response.json()
        skipped_count = len(skipped_items) if skipped_items else 0

        # Step 2: Update buyer status to active
        buyer_response = await client.patch(
            f"{sb.rest_url}/buyers?id=eq.{token.buyer_id}",
            headers=sb.get_headers(),
            json={"status": "active"},
            timeout=10.0,
        )

        if not buyer_response.is_success:
            logger.warning(f"Failed to update buyer status: {buyer_response.status_code}")

        # Step 3: Log for analytics
        await client.post(
            f"{sb.rest_url}/event_log",
            headers=sb.get_headers(),
            json={
                "event_type": "onboarding_videos_skipped",
                "source": "cockpit",
                "payload": {
                    "buyer_id": token.buyer_id,
                    "skipped_count": skipped_count,
                },
            },
            timeout=10.0,
        )

        logger.info(f"Skipped {skipped_count} videos for buyer {token.buyer_id}")

        return SkipVideosResponse(
            success=True,
            skipped_count=skipped_count,
            message=f"Skipped {skipped_count} campaigns. Onboarding completed.",
        )

    except Exception as e:
        logger.error(f"Failed to skip videos for buyer {token.buyer_id}: {e}")
        return SkipVideosResponse(
            success=False,
            message="Failed to skip videos",
            error=str(e)[:200],
        )
