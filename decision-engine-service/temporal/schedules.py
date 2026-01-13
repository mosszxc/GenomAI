"""
Temporal Schedules Management

Creates and manages scheduled workflows:
- Keitaro Poller (every hour) → triggers metrics-processor → triggers learning-loop
- Daily Recommendations (09:00 UTC)
- Maintenance (every 6 hours)
- Health Check (every 3 hours)

Usage:
    python -m temporal.schedules create
    python -m temporal.schedules delete
    python -m temporal.schedules list
"""

import asyncio
import argparse
import logging
from datetime import timedelta

from temporalio.client import Client, Schedule, ScheduleActionStartWorkflow
from temporalio.client import (
    ScheduleSpec,
    ScheduleIntervalSpec,
    ScheduleState,
    SchedulePolicy,
    ScheduleOverlapPolicy,
)

from temporal.config import settings
from temporal.client import get_temporal_client
from temporal.workflows.keitaro_polling import KeitaroPollerWorkflow, KeitaroPollerInput
from temporal.workflows.recommendation import (
    DailyRecommendationWorkflow,
    DailyRecommendationInput,
)
from temporal.workflows.maintenance import MaintenanceWorkflow, MaintenanceInput
from temporal.workflows.health_check import HealthCheckWorkflow, HealthCheckInput

# NOTE: MetricsProcessingWorkflow and LearningLoopWorkflow imports removed.
# They are now triggered as child workflows from keitaro-poller, not scheduled separately.


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Schedule definitions
SCHEDULES = {
    "keitaro-poller": {
        "workflow": KeitaroPollerWorkflow.run,
        "args": [KeitaroPollerInput(interval="yesterday", create_snapshots=True)],
        "task_queue": settings.temporal.TASK_QUEUE_METRICS,
        "interval": timedelta(hours=1),
        "execution_timeout": timedelta(minutes=30),  # Issue #553: prevent unbounded execution
        "description": "Polls Keitaro hourly, then triggers metrics-processor → learning-loop chain",
    },
    # NOTE: metrics-processor and learning-loop removed from schedules.
    # They are now triggered as child workflows:
    # keitaro-poller → metrics-processor (child) → learning-loop (child)
    "daily-recommendations": {
        "workflow": DailyRecommendationWorkflow.run,
        "args": [DailyRecommendationInput(skip_existing=True, max_recommendations=0)],
        "task_queue": settings.temporal.TASK_QUEUE_METRICS,
        "cron": "0 9 * * *",  # Daily at 09:00 UTC
        "execution_timeout": timedelta(minutes=30),
        "description": "Generates and delivers daily recommendations at 09:00 UTC",
    },
    "maintenance": {
        "workflow": MaintenanceWorkflow.run,
        "args": [
            MaintenanceInput(
                buyer_state_timeout_hours=6,
                recommendation_expiry_days=7,
                run_integrity_checks=True,
                run_cleanup=True,
            )
        ],
        "task_queue": settings.temporal.TASK_QUEUE_METRICS,
        "interval": timedelta(hours=6),
        "execution_timeout": timedelta(hours=1),
        "description": "Maintenance + cleanup every 6 hours",
    },
    "health-check": {
        "workflow": HealthCheckWorkflow.run,
        "args": [
            HealthCheckInput(
                check_supabase=True,
                check_table_sizes=True,
                check_pending=True,
                alert_on_warning=True,
                alert_on_critical=True,
            )
        ],
        "task_queue": settings.temporal.TASK_QUEUE_METRICS,
        "interval": timedelta(hours=3),
        "execution_timeout": timedelta(minutes=15),
        "description": "Health monitoring every 3 hours",
    },
}


async def create_schedule(client: Client, schedule_id: str, config: dict) -> bool:
    """Create a single schedule"""
    try:
        # Build schedule spec based on interval or cron
        if "cron" in config:
            # Parse cron expression (minute hour day month dayofweek)
            config["cron"].split()
            spec = ScheduleSpec(cron_expressions=[config["cron"]])
        else:
            spec = ScheduleSpec(intervals=[ScheduleIntervalSpec(every=config["interval"])])

        await client.create_schedule(
            schedule_id,
            Schedule(
                action=ScheduleActionStartWorkflow(
                    config["workflow"],
                    *config["args"],
                    id=f"{schedule_id}-{{{{.ScheduledTime}}}}",
                    task_queue=config["task_queue"],
                    execution_timeout=config.get("execution_timeout"),  # Issue #553
                ),
                spec=spec,
                state=ScheduleState(note=config["description"]),
                policy=SchedulePolicy(
                    overlap=ScheduleOverlapPolicy.SKIP,  # Skip if previous run still running
                    # For cron schedules (daily), allow 24h catchup to handle deploys
                    # For interval schedules, 5 min is fine as they run frequently
                    catchup_window=timedelta(hours=24)
                    if "cron" in config
                    else timedelta(minutes=5),
                ),
            ),
        )
        logger.info(f"Created schedule: {schedule_id}")
        return True
    except Exception as e:
        if "already exists" in str(e).lower():
            logger.warning(f"Schedule {schedule_id} already exists")
            return True
        logger.error(f"Failed to create schedule {schedule_id}: {e}")
        return False


async def delete_schedule(client: Client, schedule_id: str) -> bool:
    """Delete a single schedule"""
    try:
        handle = client.get_schedule_handle(schedule_id)
        await handle.delete()
        logger.info(f"Deleted schedule: {schedule_id}")
        return True
    except Exception as e:
        if "not found" in str(e).lower():
            logger.warning(f"Schedule {schedule_id} not found")
            return True
        logger.error(f"Failed to delete schedule {schedule_id}: {e}")
        return False


async def list_schedules(client: Client) -> list:
    """List all schedules"""
    schedules = []
    schedule_list = await client.list_schedules()
    async for schedule in schedule_list:
        # ScheduleListDescription has: id, info (ScheduleListInfo)
        # ScheduleListInfo has: next_action_times, recent_actions
        # ScheduleActionResult has: action, scheduled_at, started_at
        info = schedule.info
        schedules.append(
            {
                "id": schedule.id,
                "recent": info.recent_actions[0].started_at.isoformat()
                if info and info.recent_actions
                else None,
                "next": info.next_action_times[0].isoformat()
                if info and info.next_action_times
                else None,
            }
        )
    return schedules


async def create_all_schedules():
    """Create all defined schedules"""
    client = await get_temporal_client()

    logger.info("Creating all schedules...")
    success_count = 0

    for schedule_id, config in SCHEDULES.items():
        if await create_schedule(client, schedule_id, config):
            success_count += 1

    logger.info(f"Created {success_count}/{len(SCHEDULES)} schedules")
    return success_count == len(SCHEDULES)


async def delete_all_schedules():
    """Delete all defined schedules"""
    client = await get_temporal_client()

    logger.info("Deleting all schedules...")
    success_count = 0

    for schedule_id in SCHEDULES.keys():
        if await delete_schedule(client, schedule_id):
            success_count += 1

    logger.info(f"Deleted {success_count}/{len(SCHEDULES)} schedules")
    return success_count == len(SCHEDULES)


async def show_schedules():
    """Show all schedules"""
    client = await get_temporal_client()

    schedules = await list_schedules(client)

    if not schedules:
        logger.info("No schedules found")
        return

    logger.info(f"Found {len(schedules)} schedules:")
    for s in schedules:
        logger.info(f"  - {s['id']}: last={s['recent'] or 'never'}, next={s['next'] or 'unknown'}")


async def pause_schedule(schedule_id: str):
    """Pause a schedule"""
    client = await get_temporal_client()
    handle = client.get_schedule_handle(schedule_id)
    await handle.pause(note="Paused via CLI")
    logger.info(f"Paused schedule: {schedule_id}")


async def resume_schedule(schedule_id: str):
    """Resume a schedule"""
    client = await get_temporal_client()
    handle = client.get_schedule_handle(schedule_id)
    await handle.unpause(note="Resumed via CLI")
    logger.info(f"Resumed schedule: {schedule_id}")


async def trigger_schedule(schedule_id: str):
    """Trigger a schedule immediately"""
    client = await get_temporal_client()
    handle = client.get_schedule_handle(schedule_id)
    await handle.trigger()
    logger.info(f"Triggered schedule: {schedule_id}")


def main():
    """CLI entrypoint"""
    parser = argparse.ArgumentParser(description="Manage Temporal schedules")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # create command
    subparsers.add_parser("create", help="Create all schedules")

    # delete command
    subparsers.add_parser("delete", help="Delete all schedules")

    # list command
    subparsers.add_parser("list", help="List all schedules")

    # pause command
    pause_parser = subparsers.add_parser("pause", help="Pause a schedule")
    pause_parser.add_argument("schedule_id", help="Schedule ID to pause")

    # resume command
    resume_parser = subparsers.add_parser("resume", help="Resume a schedule")
    resume_parser.add_argument("schedule_id", help="Schedule ID to resume")

    # trigger command
    trigger_parser = subparsers.add_parser("trigger", help="Trigger a schedule now")
    trigger_parser.add_argument("schedule_id", help="Schedule ID to trigger")

    args = parser.parse_args()

    if args.command == "create":
        asyncio.run(create_all_schedules())
    elif args.command == "delete":
        asyncio.run(delete_all_schedules())
    elif args.command == "list":
        asyncio.run(show_schedules())
    elif args.command == "pause":
        asyncio.run(pause_schedule(args.schedule_id))
    elif args.command == "resume":
        asyncio.run(resume_schedule(args.schedule_id))
    elif args.command == "trigger":
        asyncio.run(trigger_schedule(args.schedule_id))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
