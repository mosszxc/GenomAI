"""
Module Weekly Snapshots Activities

Activities for creating and querying weekly performance snapshots of modules.
Enables trend tracking: (current_week - prev_week) / prev_week

Part of the CPA & Trend Tracking system (Issue #601).
"""

from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass

from temporalio import activity

from src.core.http_client import get_http_client
from src.core.supabase import get_supabase


def get_iso_week(dt: datetime) -> tuple[str, datetime, datetime]:
    """
    Get ISO week identifier and week boundaries.

    Returns:
        (week_id, week_start, week_end) where week_id is "YYYY-WW" format
    """
    iso_year, iso_week, _ = dt.isocalendar()
    week_id = f"{iso_year}-{iso_week:02d}"

    # Calculate week start (Monday) and end (Sunday)
    days_since_monday = dt.weekday()
    week_start = (dt - timedelta(days=days_since_monday)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)

    return week_id, week_start, week_end


@dataclass
class CreateWeeklySnapshotsInput:
    """Input for create_weekly_snapshots activity"""

    # If None, uses current week
    week_id: Optional[str] = None


@dataclass
class CreateWeeklySnapshotsOutput:
    """Output from create_weekly_snapshots activity"""

    success: bool
    week_id: str
    modules_processed: int
    snapshots_created: int
    snapshots_updated: int
    errors: list[str]


@activity.defn
async def create_weekly_snapshots(
    input: CreateWeeklySnapshotsInput,
) -> CreateWeeklySnapshotsOutput:
    """
    Create weekly snapshots for all active modules.

    For each module, captures current metrics and calculates trend vs previous week.
    Should be run once per week (e.g., Sunday night or Monday morning).

    Idempotent: uses upsert to handle re-runs for same week.

    Args:
        input: Optional week_id override (defaults to current week)

    Returns:
        CreateWeeklySnapshotsOutput with counts
    """
    now = datetime.utcnow()
    week_id, week_start, week_end = get_iso_week(now)

    if input.week_id:
        week_id = input.week_id
        # Parse week_id to get dates (YYYY-WW format)
        year, week_num = map(int, week_id.split("-"))
        # First day of the year
        jan1 = datetime(year, 1, 1)
        # First Monday of the year
        first_monday = jan1 + timedelta(days=(7 - jan1.weekday()) % 7)
        if jan1.weekday() == 0:
            first_monday = jan1
        week_start = first_monday + timedelta(weeks=week_num - 1)
        week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)

    activity.logger.info(f"Creating weekly snapshots for week {week_id}")

    sb = get_supabase()
    headers = sb.get_headers(for_write=True)
    read_headers = sb.get_headers()

    errors: list[str] = []
    modules_processed = 0
    snapshots_created = 0
    snapshots_updated = 0

    try:
        client = get_http_client()

        # Get all modules with status != 'dead'
        modules_url = (
            f"{sb.rest_url}/module_bank"
            f"?status=neq.dead"
            f"&select=id,sample_size,win_count,loss_count,total_spend,total_revenue,total_conversions"
        )
        response = await client.get(modules_url, headers=read_headers, timeout=30.0)
        response.raise_for_status()
        modules = response.json()

        activity.logger.info(f"Found {len(modules)} modules to snapshot")

        # Calculate previous week for trend comparison
        prev_week_id, _, _ = get_iso_week(week_start - timedelta(days=7))

        for module in modules:
            module_id = module["id"]
            modules_processed += 1

            try:
                # Get previous week snapshot for trend calculation
                prev_url = (
                    f"{sb.rest_url}/module_weekly_snapshots"
                    f"?module_id=eq.{module_id}"
                    f"&week_id=eq.{prev_week_id}"
                    f"&select=sample_size,win_count,total_spend,total_conversions,win_rate,avg_cpa,avg_roi"
                    f"&limit=1"
                )
                prev_response = await client.get(prev_url, headers=read_headers, timeout=15.0)
                prev_response.raise_for_status()
                prev_data = prev_response.json()
                prev_snapshot = prev_data[0] if prev_data else None

                # Current metrics
                sample_size = module.get("sample_size") or 0
                win_count = module.get("win_count") or 0
                loss_count = module.get("loss_count") or 0
                total_spend = float(module.get("total_spend") or 0)
                total_revenue = float(module.get("total_revenue") or 0)
                total_conversions = module.get("total_conversions") or 0

                # Calculate trends if previous snapshot exists
                win_rate_trend = None
                cpa_trend = None
                roi_trend = None
                sample_size_delta = sample_size
                win_count_delta = win_count
                spend_delta = total_spend
                conversions_delta = total_conversions

                if prev_snapshot:
                    prev_sample = prev_snapshot.get("sample_size") or 0
                    prev_win_count = prev_snapshot.get("win_count") or 0
                    prev_spend = float(prev_snapshot.get("total_spend") or 0)
                    prev_conversions = prev_snapshot.get("total_conversions") or 0
                    prev_win_rate = float(prev_snapshot.get("win_rate") or 0)
                    prev_cpa = prev_snapshot.get("avg_cpa")
                    prev_roi = float(prev_snapshot.get("avg_roi") or 0)

                    # Deltas
                    sample_size_delta = sample_size - prev_sample
                    win_count_delta = win_count - prev_win_count
                    spend_delta = total_spend - prev_spend
                    conversions_delta = total_conversions - prev_conversions

                    # Trend calculations: (current - prev) / prev
                    # win_rate trend
                    current_win_rate = win_count / sample_size if sample_size > 0 else 0
                    if prev_win_rate > 0:
                        win_rate_trend = (current_win_rate - prev_win_rate) / prev_win_rate

                    # CPA trend (negative is better)
                    current_cpa = total_spend / total_conversions if total_conversions > 0 else None
                    if prev_cpa and prev_cpa > 0 and current_cpa is not None:
                        cpa_trend = (current_cpa - prev_cpa) / prev_cpa

                    # ROI trend
                    current_roi = (
                        (total_revenue - total_spend) / total_spend if total_spend > 0 else 0
                    )
                    if prev_roi != 0:
                        roi_trend = (current_roi - prev_roi) / abs(prev_roi)

                # Upsert snapshot
                snapshot_payload = {
                    "module_id": module_id,
                    "week_id": week_id,
                    "week_start": week_start.date().isoformat(),
                    "week_end": week_end.date().isoformat(),
                    "sample_size": sample_size,
                    "win_count": win_count,
                    "loss_count": loss_count,
                    "total_spend": total_spend,
                    "total_revenue": total_revenue,
                    "total_conversions": total_conversions,
                    "win_rate_trend": win_rate_trend,
                    "cpa_trend": cpa_trend,
                    "roi_trend": roi_trend,
                    "sample_size_delta": sample_size_delta,
                    "win_count_delta": win_count_delta,
                    "spend_delta": spend_delta,
                    "conversions_delta": conversions_delta,
                }

                # Check if snapshot exists
                check_url = (
                    f"{sb.rest_url}/module_weekly_snapshots"
                    f"?module_id=eq.{module_id}&week_id=eq.{week_id}&select=id"
                )
                check_response = await client.get(check_url, headers=read_headers, timeout=15.0)
                check_response.raise_for_status()
                existing = check_response.json()

                if existing:
                    # Update existing
                    update_url = f"{sb.rest_url}/module_weekly_snapshots?id=eq.{existing[0]['id']}"
                    response = await client.patch(
                        update_url, headers=headers, json=snapshot_payload
                    )
                    response.raise_for_status()
                    snapshots_updated += 1
                else:
                    # Create new
                    create_url = f"{sb.rest_url}/module_weekly_snapshots"
                    response = await client.post(create_url, headers=headers, json=snapshot_payload)
                    response.raise_for_status()
                    snapshots_created += 1

            except Exception as e:
                errors.append(f"Module {module_id}: {str(e)}")

        activity.logger.info(
            f"Weekly snapshots complete: {snapshots_created} created, "
            f"{snapshots_updated} updated, {len(errors)} errors"
        )

        return CreateWeeklySnapshotsOutput(
            success=len(errors) == 0,
            week_id=week_id,
            modules_processed=modules_processed,
            snapshots_created=snapshots_created,
            snapshots_updated=snapshots_updated,
            errors=errors,
        )

    except Exception as e:
        activity.logger.error(f"Weekly snapshots failed: {str(e)}")
        return CreateWeeklySnapshotsOutput(
            success=False,
            week_id=week_id,
            modules_processed=0,
            snapshots_created=0,
            snapshots_updated=0,
            errors=[str(e)],
        )


@dataclass
class GetModuleTrendInput:
    """Input for get_module_trend activity"""

    module_id: str
    weeks: int = 4  # Number of weeks to fetch


@dataclass
class WeekSnapshot:
    """Single week snapshot data"""

    week_id: str
    week_start: str
    avg_cpa: Optional[float]
    win_rate: float
    cpa_trend: Optional[float]
    win_rate_trend: Optional[float]
    sample_size: int
    sample_size_delta: int


@dataclass
class GetModuleTrendOutput:
    """Output from get_module_trend activity"""

    module_id: str
    snapshots: list[WeekSnapshot]
    overall_cpa_trend: Optional[float]  # Trend over entire period
    overall_win_rate_trend: Optional[float]


@activity.defn
async def get_module_trend(input: GetModuleTrendInput) -> GetModuleTrendOutput:
    """
    Get trend data for a module over last N weeks.

    Returns weekly snapshots and calculates overall trend direction.

    Args:
        input: module_id and number of weeks

    Returns:
        GetModuleTrendOutput with snapshots and trends
    """
    activity.logger.info(f"Getting trend for module {input.module_id} ({input.weeks} weeks)")

    sb = get_supabase()
    headers = sb.get_headers()

    try:
        client = get_http_client()

        # Get recent snapshots
        url = (
            f"{sb.rest_url}/module_weekly_snapshots"
            f"?module_id=eq.{input.module_id}"
            f"&select=week_id,week_start,avg_cpa,win_rate,cpa_trend,win_rate_trend,sample_size,sample_size_delta"
            f"&order=week_start.desc"
            f"&limit={input.weeks}"
        )
        response = await client.get(url, headers=headers, timeout=15.0)
        response.raise_for_status()
        data = response.json()

        snapshots = [
            WeekSnapshot(
                week_id=row["week_id"],
                week_start=row["week_start"],
                avg_cpa=row.get("avg_cpa"),
                win_rate=float(row.get("win_rate") or 0),
                cpa_trend=row.get("cpa_trend"),
                win_rate_trend=row.get("win_rate_trend"),
                sample_size=row.get("sample_size") or 0,
                sample_size_delta=row.get("sample_size_delta") or 0,
            )
            for row in data
        ]

        # Calculate overall trends (first vs last in period)
        overall_cpa_trend = None
        overall_win_rate_trend = None

        if len(snapshots) >= 2:
            newest = snapshots[0]
            oldest = snapshots[-1]

            # CPA trend over period
            if newest.avg_cpa is not None and oldest.avg_cpa is not None and oldest.avg_cpa > 0:
                overall_cpa_trend = (newest.avg_cpa - oldest.avg_cpa) / oldest.avg_cpa

            # Win rate trend over period
            if oldest.win_rate > 0:
                overall_win_rate_trend = (newest.win_rate - oldest.win_rate) / oldest.win_rate

        activity.logger.info(
            f"Module trend: {len(snapshots)} weeks, "
            f"overall CPA trend={overall_cpa_trend}, win_rate trend={overall_win_rate_trend}"
        )

        return GetModuleTrendOutput(
            module_id=input.module_id,
            snapshots=snapshots,
            overall_cpa_trend=overall_cpa_trend,
            overall_win_rate_trend=overall_win_rate_trend,
        )

    except Exception as e:
        activity.logger.error(f"Failed to get module trend: {str(e)}")
        return GetModuleTrendOutput(
            module_id=input.module_id,
            snapshots=[],
            overall_cpa_trend=None,
            overall_win_rate_trend=None,
        )


@dataclass
class GetTrendingModulesInput:
    """Input for get_trending_modules activity"""

    module_type: Optional[str] = None  # hook, promise, proof
    trend_direction: str = "improving"  # improving or declining
    limit: int = 10


@dataclass
class TrendingModule:
    """Module with trend info"""

    module_id: str
    module_type: str
    avg_cpa: Optional[float]
    cpa_trend: Optional[float]
    win_rate: float
    win_rate_trend: Optional[float]
    sample_size: int


@dataclass
class GetTrendingModulesOutput:
    """Output from get_trending_modules activity"""

    modules: list[TrendingModule]
    trend_direction: str


@activity.defn
async def get_trending_modules(input: GetTrendingModulesInput) -> GetTrendingModulesOutput:
    """
    Get modules with improving or declining trends.

    Useful for identifying:
    - Rising stars (improving CPA, increasing win rate)
    - Fatiguing modules (declining metrics)

    Args:
        input: filters and limit

    Returns:
        GetTrendingModulesOutput with trending modules
    """
    activity.logger.info(f"Getting {input.trend_direction} modules (limit: {input.limit})")

    sb = get_supabase()
    headers = sb.get_headers()

    try:
        client = get_http_client()

        # Get latest week
        now = datetime.utcnow()
        week_id, _, _ = get_iso_week(now)

        # Build query
        url = f"{sb.rest_url}/module_weekly_snapshots"
        url += f"?week_id=eq.{week_id}"

        # Filter by trend direction
        if input.trend_direction == "improving":
            # Improving = negative CPA trend (lower is better) OR positive win_rate trend
            url += "&or=(cpa_trend.lt.0,win_rate_trend.gt.0)"
            url += "&order=cpa_trend.asc.nullslast"
        else:  # declining
            url += "&or=(cpa_trend.gt.0,win_rate_trend.lt.0)"
            url += "&order=cpa_trend.desc.nullslast"

        url += "&select=module_id,avg_cpa,cpa_trend,win_rate,win_rate_trend,sample_size"
        url += f"&limit={input.limit}"

        response = await client.get(url, headers=headers, timeout=15.0)
        response.raise_for_status()
        snapshots = response.json()

        if not snapshots:
            return GetTrendingModulesOutput(modules=[], trend_direction=input.trend_direction)

        # Get module details
        module_ids = [s["module_id"] for s in snapshots]
        modules_url = (
            f"{sb.rest_url}/module_bank?id=in.({','.join(module_ids)})&select=id,module_type"
        )
        if input.module_type:
            modules_url += f"&module_type=eq.{input.module_type}"

        modules_response = await client.get(modules_url, headers=headers, timeout=15.0)
        modules_response.raise_for_status()
        modules_data = {m["id"]: m for m in modules_response.json()}

        # Combine data
        result = []
        for snapshot in snapshots:
            module_id = snapshot["module_id"]
            if module_id not in modules_data:
                continue

            module = modules_data[module_id]
            if input.module_type and module["module_type"] != input.module_type:
                continue

            result.append(
                TrendingModule(
                    module_id=module_id,
                    module_type=module["module_type"],
                    avg_cpa=snapshot.get("avg_cpa"),
                    cpa_trend=snapshot.get("cpa_trend"),
                    win_rate=float(snapshot.get("win_rate") or 0),
                    win_rate_trend=snapshot.get("win_rate_trend"),
                    sample_size=snapshot.get("sample_size") or 0,
                )
            )

        activity.logger.info(f"Found {len(result)} {input.trend_direction} modules")

        return GetTrendingModulesOutput(modules=result, trend_direction=input.trend_direction)

    except Exception as e:
        activity.logger.error(f"Failed to get trending modules: {str(e)}")
        return GetTrendingModulesOutput(modules=[], trend_direction=input.trend_direction)
