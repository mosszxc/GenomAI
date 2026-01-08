"""
Temporal Schedules Management

Creates and manages scheduled workflows:
- Keitaro Poller (every 10 minutes)
- Metrics Processing (every 30 minutes)
- Learning Loop (every hour)

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
from temporal.workflows.metrics_processing import MetricsProcessingWorkflow, MetricsProcessingInput
from temporal.workflows.learning_loop import LearningLoopWorkflow, LearningLoopInput


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Schedule definitions
SCHEDULES = {
    "keitaro-poller": {
        "workflow": KeitaroPollerWorkflow.run,
        "args": [KeitaroPollerInput(interval="yesterday", create_snapshots=True)],
        "task_queue": settings.temporal.TASK_QUEUE_METRICS,
        "interval": timedelta(minutes=10),
        "description": "Polls Keitaro for metrics every 10 minutes",
    },
    "metrics-processor": {
        "workflow": MetricsProcessingWorkflow.run,
        "args": [MetricsProcessingInput(batch_limit=50, trigger_learning=True)],
        "task_queue": settings.temporal.TASK_QUEUE_METRICS,
        "interval": timedelta(minutes=30),
        "description": "Processes metrics snapshots into outcomes every 30 minutes",
    },
    "learning-loop": {
        "workflow": LearningLoopWorkflow.run,
        "args": [LearningLoopInput(batch_limit=100, process_individually=False)],
        "task_queue": settings.temporal.TASK_QUEUE_METRICS,
        "interval": timedelta(hours=1),
        "description": "Runs learning loop every hour",
    },
}


async def create_schedule(client: Client, schedule_id: str, config: dict) -> bool:
    """Create a single schedule"""
    try:
        handle = await client.create_schedule(
            schedule_id,
            Schedule(
                action=ScheduleActionStartWorkflow(
                    config["workflow"],
                    *config["args"],
                    id=f"{schedule_id}-{{{{.ScheduledTime}}}}",
                    task_queue=config["task_queue"],
                ),
                spec=ScheduleSpec(
                    intervals=[
                        ScheduleIntervalSpec(every=config["interval"])
                    ]
                ),
                state=ScheduleState(
                    note=config["description"]
                ),
                policy=SchedulePolicy(
                    overlap=ScheduleOverlapPolicy.SKIP,  # Skip if previous run still running
                    catchup_window=timedelta(minutes=5)  # Don't catch up missed runs
                )
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
    async for schedule in client.list_schedules():
        schedules.append({
            "id": schedule.id,
            "state": schedule.info.schedule.state.note if schedule.info.schedule.state else "",
            "running": len(schedule.info.running_workflows) > 0,
            "recent": schedule.info.recent_actions[0].start_time.isoformat() if schedule.info.recent_actions else None
        })
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
        status = "RUNNING" if s["running"] else "IDLE"
        logger.info(
            f"  - {s['id']}: {status} "
            f"(last: {s['recent'] or 'never'})"
        )


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
