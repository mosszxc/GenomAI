"""
Temporal Schedules API routes

Provides REST API for viewing and managing Temporal schedules:
- GET /api/schedules - List all schedules
- GET /api/schedules/{id} - Get schedule details
- POST /api/schedules/{id}/trigger - Trigger schedule (requires API key)
"""

import os
from datetime import timedelta
from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel
from typing import Optional


router = APIRouter()


# Schedule definitions (mirrored from temporal/schedules.py for display)
SCHEDULE_DEFINITIONS = {
    "keitaro-poller": {
        "interval": "10m",
        "description": "Polls Keitaro for metrics every 10 minutes",
    },
    "metrics-processor": {
        "interval": "30m",
        "description": "Processes metrics snapshots into outcomes every 30 minutes",
    },
    "learning-loop": {
        "interval": "1h",
        "description": "Runs learning loop every hour",
    },
    "daily-recommendations": {
        "cron": "0 9 * * *",
        "description": "Generates and delivers daily recommendations at 09:00 UTC",
    },
    "maintenance": {
        "interval": "6h",
        "description": "Maintenance tasks every 6 hours: cleanup stale states, expire recommendations",
    },
}


class ScheduleInfo(BaseModel):
    """Schedule information"""

    id: str
    status: str
    interval: Optional[str] = None
    cron: Optional[str] = None
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    paused: bool = False
    description: Optional[str] = None


class ScheduleListResponse(BaseModel):
    """Response for list schedules"""

    success: bool
    schedules: list[ScheduleInfo]


class ScheduleDetailResponse(BaseModel):
    """Response for schedule details"""

    success: bool
    schedule: Optional[ScheduleInfo] = None
    error: Optional[str] = None


class TriggerResponse(BaseModel):
    """Response for trigger action"""

    success: bool
    message: str


async def verify_api_key(x_api_key: Optional[str] = Header(None)):
    """
    Verify API Key from X-API-Key header

    Args:
        x_api_key: X-API-Key header value

    Returns:
        bool: True if valid

    Raises:
        HTTPException: If API key is invalid
    """
    api_key = os.getenv("API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="API_KEY not configured")

    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")

    if x_api_key != api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return True


def format_interval(delta: timedelta) -> str:
    """Format timedelta to human-readable string"""
    total_seconds = int(delta.total_seconds())
    if total_seconds >= 3600:
        hours = total_seconds // 3600
        return f"{hours}h"
    elif total_seconds >= 60:
        minutes = total_seconds // 60
        return f"{minutes}m"
    return f"{total_seconds}s"


@router.get(
    "",
    response_model=ScheduleListResponse,
    summary="List all schedules",
    description="Returns list of all Temporal schedules with their status",
)
async def list_schedules() -> ScheduleListResponse:
    """
    GET /api/schedules

    List all Temporal schedules with their current status.
    """
    try:
        from temporal.client import get_temporal_client

        client = await get_temporal_client()

        schedules = []
        schedule_list = await client.list_schedules()
        async for schedule in schedule_list:
            # ScheduleListDescription has: id, info (ScheduleListInfo)
            # ScheduleListInfo has: next_action_times, recent_actions
            schedule_id = schedule.id
            info = schedule.info

            # Get definition info (interval/cron/description from our definitions)
            definition = SCHEDULE_DEFINITIONS.get(schedule_id, {})
            interval_str = definition.get("interval")
            cron_str = definition.get("cron")

            # Get timing info
            last_run = None
            if info.recent_actions:
                last_run = info.recent_actions[0].started_at.isoformat()

            next_run = None
            if info.next_action_times:
                next_run = info.next_action_times[0].isoformat()

            # Status: active if has next_run scheduled
            status = "active" if next_run else "idle"

            schedules.append(
                ScheduleInfo(
                    id=schedule_id,
                    status=status,
                    interval=interval_str,
                    cron=cron_str,
                    last_run=last_run,
                    next_run=next_run,
                    paused=False,  # Not available in list, use GET /{id} for details
                    description=definition.get("description"),
                )
            )

        return ScheduleListResponse(success=True, schedules=schedules)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list schedules: {e}")


@router.get(
    "/{schedule_id}",
    response_model=ScheduleDetailResponse,
    summary="Get schedule details",
    description="Returns detailed information about a specific schedule",
)
async def get_schedule(schedule_id: str) -> ScheduleDetailResponse:
    """
    GET /api/schedules/{id}

    Get detailed information about a specific schedule.
    """
    try:
        from temporal.client import get_temporal_client

        client = await get_temporal_client()

        handle = client.get_schedule_handle(schedule_id)
        desc = await handle.describe()

        # Get definition info
        definition = SCHEDULE_DEFINITIONS.get(schedule_id, {})

        # Get spec info
        spec = desc.schedule.spec

        # Determine interval or cron
        interval_str = definition.get("interval")
        cron_str = definition.get("cron")

        if spec:
            if spec.intervals:
                interval_str = format_interval(spec.intervals[0].every)
            if spec.cron_expressions:
                cron_str = spec.cron_expressions[0]

        # Check if paused
        paused = False
        if desc.schedule.state:
            paused = desc.schedule.state.paused

        # Get timing info
        last_run = None
        if desc.info.recent_actions:
            last_run = desc.info.recent_actions[0].started_at.isoformat()

        next_run = None
        if desc.info.next_action_times:
            next_run = desc.info.next_action_times[0].isoformat()

        # Determine status
        if paused:
            status = "paused"
        elif next_run:
            status = "active"
        else:
            status = "idle"

        schedule_info = ScheduleInfo(
            id=schedule_id,
            status=status,
            interval=interval_str,
            cron=cron_str,
            last_run=last_run,
            next_run=next_run,
            paused=paused,
            description=definition.get("description"),
        )

        return ScheduleDetailResponse(success=True, schedule=schedule_info)

    except Exception as e:
        error_str = str(e).lower()
        if "not found" in error_str or "does not exist" in error_str:
            raise HTTPException(
                status_code=404, detail=f"Schedule '{schedule_id}' not found"
            )
        raise HTTPException(status_code=500, detail=f"Failed to get schedule: {e}")


@router.post(
    "/{schedule_id}/trigger",
    response_model=TriggerResponse,
    summary="Trigger schedule",
    description="Manually trigger a schedule to run immediately. Requires API key.",
)
async def trigger_schedule(
    schedule_id: str, _: bool = Depends(verify_api_key)
) -> TriggerResponse:
    """
    POST /api/schedules/{id}/trigger

    Manually trigger a schedule to run immediately.
    Requires X-API-Key header.
    """
    try:
        from temporal.client import get_temporal_client

        client = await get_temporal_client()

        handle = client.get_schedule_handle(schedule_id)
        await handle.trigger()

        return TriggerResponse(
            success=True,
            message=f"Schedule '{schedule_id}' triggered successfully",
        )

    except Exception as e:
        error_str = str(e).lower()
        if "not found" in error_str or "does not exist" in error_str:
            raise HTTPException(
                status_code=404, detail=f"Schedule '{schedule_id}' not found"
            )
        raise HTTPException(status_code=500, detail=f"Failed to trigger schedule: {e}")
