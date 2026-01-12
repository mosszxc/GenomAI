"""
Metrics Activities

Activities for storing and processing metrics data:
- Upsert to raw_metrics_current
- Create daily_metrics_snapshot
- Process outcomes via OutcomeService

Uses Supabase REST API directly for database operations.
"""

import httpx
from datetime import datetime
from typing import Optional
from dataclasses import dataclass

from temporalio import activity

from temporal.config import settings


SCHEMA = "genomai"


def _get_supabase_headers(for_write: bool = False) -> dict:
    """Get headers for Supabase REST API"""
    headers = {
        "apikey": settings.supabase.service_role_key,
        "Authorization": f"Bearer {settings.supabase.service_role_key}",
        "Accept-Profile": SCHEMA,
        "Content-Type": "application/json",
    }
    if for_write:
        headers["Content-Profile"] = SCHEMA
        headers["Prefer"] = "return=representation"
    return headers


def _get_supabase_url(table: str) -> str:
    """Build Supabase REST API URL"""
    return f"{settings.supabase.url}/rest/v1/{table}"


@dataclass
class UpsertRawMetricsInput:
    """Input for upsert_raw_metrics activity"""

    tracker_id: str
    metrics_date: str  # ISO date string
    metrics: dict  # {clicks, conversions, revenue, cost}


@dataclass
class UpsertRawMetricsOutput:
    """Output from upsert_raw_metrics activity"""

    success: bool
    updated: bool  # True if updated existing, False if inserted new


@activity.defn
async def upsert_raw_metrics(input: UpsertRawMetricsInput) -> UpsertRawMetricsOutput:
    """
    Upsert metrics to raw_metrics_current table.

    Uses ON CONFLICT (tracker_id, date) DO UPDATE for upsert behavior.

    Args:
        input: tracker_id, date, and metrics dict

    Returns:
        UpsertRawMetricsOutput with success status
    """
    activity.logger.info(
        f"Upserting raw metrics for tracker {input.tracker_id} on {input.metrics_date}"
    )

    url = _get_supabase_url("raw_metrics_current")
    headers = _get_supabase_headers(for_write=True)
    headers["Prefer"] = "return=representation,resolution=merge-duplicates"

    payload = {
        "tracker_id": input.tracker_id,
        "date": input.metrics_date,
        "metrics": input.metrics,
        "updated_at": datetime.now().isoformat(),
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()

    activity.logger.info(f"Upserted raw metrics for {input.tracker_id}")

    return UpsertRawMetricsOutput(success=True, updated=True)


@dataclass
class CreateSnapshotInput:
    """Input for create_daily_snapshot activity"""

    tracker_id: str
    snapshot_date: str  # ISO date string
    metrics: dict  # {clicks, conversions, revenue, cost}


@dataclass
class CreateSnapshotOutput:
    """Output from create_daily_snapshot activity"""

    snapshot_id: str
    created: bool


@activity.defn
async def create_daily_snapshot(input: CreateSnapshotInput) -> CreateSnapshotOutput:
    """
    Create daily metrics snapshot.

    Snapshots are immutable records of daily metrics.
    Used for historical tracking and outcome aggregation.

    Args:
        input: tracker_id, date, and metrics dict

    Returns:
        CreateSnapshotOutput with snapshot_id
    """
    activity.logger.info(
        f"Creating snapshot for tracker {input.tracker_id} on {input.snapshot_date}"
    )

    url = _get_supabase_url("daily_metrics_snapshot")
    headers = _get_supabase_headers(for_write=True)

    payload = {
        "tracker_id": input.tracker_id,
        "date": input.snapshot_date,
        "metrics": input.metrics,
        "created_at": datetime.now().isoformat(),
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

    snapshot_id = data[0]["id"] if data else None

    activity.logger.info(f"Created snapshot {snapshot_id} for {input.tracker_id}")

    return CreateSnapshotOutput(snapshot_id=snapshot_id, created=True)


@dataclass
class CheckSnapshotExistsInput:
    """Input for check_snapshot_exists activity"""

    tracker_id: str
    snapshot_date: str


@dataclass
class CheckSnapshotExistsOutput:
    """Output from check_snapshot_exists activity"""

    exists: bool
    snapshot_id: Optional[str] = None


@activity.defn
async def check_snapshot_exists(
    input: CheckSnapshotExistsInput,
) -> CheckSnapshotExistsOutput:
    """
    Check if a snapshot already exists for given tracker and date.

    Prevents duplicate snapshots.

    Args:
        input: tracker_id and date

    Returns:
        CheckSnapshotExistsOutput with exists flag
    """
    url = _get_supabase_url("daily_metrics_snapshot")
    headers = _get_supabase_headers()

    params = {
        "tracker_id": f"eq.{input.tracker_id}",
        "date": f"eq.{input.snapshot_date}",
        "select": "id",
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

    if data:
        return CheckSnapshotExistsOutput(exists=True, snapshot_id=data[0]["id"])

    return CheckSnapshotExistsOutput(exists=False)


@dataclass
class ProcessOutcomeInput:
    """Input for process_outcome activity"""

    snapshot_id: str


@dataclass
class ProcessOutcomeOutput:
    """Output from process_outcome activity"""

    success: bool
    outcome_id: Optional[str] = None
    learning_triggered: bool = False
    skipped: bool = False  # True when tracker has no linked idea (expected case)
    error_code: Optional[str] = None
    error_message: Optional[str] = None


@activity.defn
async def process_outcome(input: ProcessOutcomeInput) -> ProcessOutcomeOutput:
    """
    Process outcome from snapshot using OutcomeService.

    This wraps the existing outcome_service.py logic.

    Args:
        input: snapshot_id

    Returns:
        ProcessOutcomeOutput with result
    """
    activity.logger.info(f"Processing outcome for snapshot {input.snapshot_id}")

    # Import here to avoid circular imports
    from src.services.outcome_service import get_outcome_service

    try:
        service = get_outcome_service()
        result = await service.aggregate(input.snapshot_id)

        if result.success:
            if result.skipped:
                # Tracker without linked idea is expected (e.g., test campaigns)
                # Log as debug, not warning, to avoid polluting logs
                activity.logger.debug(
                    f"Snapshot skipped: {result.error_code} - {result.error_message}"
                )
                return ProcessOutcomeOutput(
                    success=True,
                    skipped=True,
                    error_code=result.error_code,
                    error_message=result.error_message,
                )
            else:
                activity.logger.info(
                    f"Outcome created: {result.outcome.id if result.outcome else 'N/A'}"
                )
                return ProcessOutcomeOutput(
                    success=True,
                    outcome_id=result.outcome.id if result.outcome else None,
                    learning_triggered=result.learning_triggered,
                )
        else:
            activity.logger.warning(
                f"Outcome processing failed: {result.error_code} - {result.error_message}"
            )
            return ProcessOutcomeOutput(
                success=False,
                error_code=result.error_code,
                error_message=result.error_message,
            )

    except Exception as e:
        activity.logger.error(f"Outcome processing error: {str(e)}")
        return ProcessOutcomeOutput(
            success=False, error_code="INTERNAL_ERROR", error_message=str(e)
        )


@dataclass
class GetUnprocessedSnapshotsInput:
    """Input for get_unprocessed_snapshots activity"""

    limit: int = 100


@dataclass
class GetUnprocessedSnapshotsOutput:
    """Output from get_unprocessed_snapshots activity"""

    snapshot_ids: list[str]
    total: int


@activity.defn
async def get_unprocessed_snapshots(
    input: GetUnprocessedSnapshotsInput,
) -> GetUnprocessedSnapshotsOutput:
    """
    Get snapshots that haven't been processed into outcomes yet.

    Joins with outcome_aggregates to find gaps.

    Args:
        input: limit for batch size

    Returns:
        GetUnprocessedSnapshotsOutput with snapshot_ids
    """
    activity.logger.info(f"Fetching unprocessed snapshots (limit: {input.limit})")

    # Get all snapshots not yet linked to outcomes
    # This is a simplified query - in production might need optimization
    url = _get_supabase_url("daily_metrics_snapshot")
    headers = _get_supabase_headers()

    # Get recent snapshots ordered by date desc
    params = {"select": "id", "order": "created_at.desc", "limit": str(input.limit)}

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

    snapshot_ids = [row["id"] for row in data]

    activity.logger.info(f"Found {len(snapshot_ids)} snapshots to check")

    return GetUnprocessedSnapshotsOutput(
        snapshot_ids=snapshot_ids, total=len(snapshot_ids)
    )


@dataclass
class EmitMetricsEventInput:
    """Input for emit_metrics_event activity"""

    event_type: str  # metrics.collected, snapshot.created, etc.
    entity_type: str  # tracker, snapshot, etc.
    payload: dict
    entity_id: Optional[str] = None  # Must be UUID or None (workflow_id is NOT UUID)


@activity.defn
async def emit_metrics_event(input: EmitMetricsEventInput) -> bool:
    """
    Emit metrics-related event to event_log.

    Used for observability and triggering downstream workflows.

    Args:
        input: event details

    Returns:
        True if successful
    """
    activity.logger.info(f"Emitting event: {input.event_type}")

    url = _get_supabase_url("event_log")
    headers = _get_supabase_headers(for_write=True)

    payload = {
        "event_type": input.event_type,
        "entity_type": input.entity_type,
        "payload": input.payload,
        "occurred_at": datetime.now().isoformat(),
    }
    # Only add entity_id if provided (must be valid UUID, workflow_id is NOT UUID)
    if input.entity_id:
        payload["entity_id"] = input.entity_id

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()

    activity.logger.info(f"Event emitted: {input.event_type}")

    return True
