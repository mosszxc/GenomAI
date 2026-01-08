"""
Temporal Worker Entrypoint

Runs Temporal workers that execute workflows and activities.
This is the main entry point for the Temporal worker process.

Usage:
    python -m temporal.worker

Environment:
    TEMPORAL_ADDRESS: Temporal server address
    TEMPORAL_NAMESPACE: Temporal namespace
    TEMPORAL_API_KEY: API key (for Temporal Cloud)
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from temporalio.client import Client
from temporalio.worker import Worker

from temporal.config import settings
from temporal.client import get_temporal_client

# Import workflows
from temporal.workflows.creative_pipeline import CreativePipelineWorkflow
from temporal.workflows.keitaro_polling import KeitaroPollerWorkflow
from temporal.workflows.metrics_processing import MetricsProcessingWorkflow
from temporal.workflows.learning_loop import LearningLoopWorkflow
from temporal.workflows.recommendation import (
    DailyRecommendationWorkflow,
    SingleRecommendationDeliveryWorkflow,
)
from temporal.workflows.maintenance import MaintenanceWorkflow

# Import activities - Supabase
from temporal.activities.supabase import (
    get_creative,
    get_idea,
    check_idea_exists,
    create_idea,
    save_decomposed_creative,
    update_creative_status,
    emit_event,
)

# Import activities - Decision Engine
from temporal.activities.decision_engine import make_decision
from temporal.activities.transcription import (
    transcribe_audio,
    get_transcript,
)
from temporal.activities.llm_decomposition import (
    decompose_creative,
    validate_decomposition,
)
from temporal.activities.hypothesis_generation import (
    generate_hypotheses,
    save_hypotheses,
)
from temporal.activities.telegram import (
    send_hypothesis_to_telegram,
    get_buyer_chat_id,
    update_hypothesis_delivery_status,
    emit_delivery_event,
)

# Import activities - Keitaro
from temporal.activities.keitaro import (
    get_all_trackers,
    get_tracker_metrics,
    get_batch_metrics,
)

# Import activities - Metrics
from temporal.activities.metrics import (
    upsert_raw_metrics,
    create_daily_snapshot,
    check_snapshot_exists,
    process_outcome,
    get_unprocessed_snapshots,
    emit_metrics_event,
)

# Import activities - Learning
from temporal.activities.learning import (
    process_learning_batch,
    get_unprocessed_outcomes,
    process_single_outcome,
    check_death_conditions,
    emit_learning_event,
)

# Import activities - Recommendation
from temporal.activities.recommendation import (
    get_active_buyers,
    generate_recommendation_for_buyer,
    send_recommendation_to_telegram,
    update_recommendation_delivery,
    emit_recommendation_event,
    get_recommendation_by_id,
    check_existing_daily_recommendation,
)

# Import activities - Maintenance
from temporal.activities.maintenance import (
    reset_stale_buyer_states,
    expire_old_recommendations,
    check_data_integrity,
    emit_maintenance_event,
)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def run_worker():
    """Run Temporal worker with all workflows and activities."""

    logger.info(f"Connecting to Temporal at {settings.temporal.address}")
    logger.info(f"Namespace: {settings.temporal.namespace}")

    # Get Temporal client
    client = await get_temporal_client()

    logger.info("Connected to Temporal")

    # Create worker for creative pipeline
    worker = Worker(
        client,
        task_queue=settings.temporal.TASK_QUEUE_CREATIVE_PIPELINE,
        workflows=[
            CreativePipelineWorkflow,
        ],
        activities=[
            # Supabase activities
            get_creative,
            get_idea,
            check_idea_exists,
            create_idea,
            save_decomposed_creative,
            update_creative_status,
            emit_event,
            # Decision Engine
            make_decision,
            # Transcription (AssemblyAI)
            transcribe_audio,
            get_transcript,
            # LLM Decomposition (OpenAI)
            decompose_creative,
            validate_decomposition,
            # Hypothesis Generation
            generate_hypotheses,
            save_hypotheses,
            # Telegram Delivery
            send_hypothesis_to_telegram,
            get_buyer_chat_id,
            update_hypothesis_delivery_status,
            emit_delivery_event,
        ],
    )

    logger.info(f"Starting worker on queue: {settings.temporal.TASK_QUEUE_CREATIVE_PIPELINE}")
    logger.info("Registered workflows: CreativePipelineWorkflow")
    logger.info("Press Ctrl+C to stop")

    # Run worker
    await worker.run()


async def run_all_workers():
    """
    Run all workers concurrently.

    Runs:
    - Creative Pipeline worker (creative-pipeline queue)
    - Metrics worker (metrics queue) - Keitaro, Metrics, Learning
    """

    logger.info("Starting GenomAI Temporal Workers")

    client = await get_temporal_client()

    # Creative Pipeline Worker
    creative_worker = Worker(
        client,
        task_queue=settings.temporal.TASK_QUEUE_CREATIVE_PIPELINE,
        workflows=[CreativePipelineWorkflow],
        activities=[
            # Supabase activities
            get_creative,
            get_idea,
            check_idea_exists,
            create_idea,
            save_decomposed_creative,
            update_creative_status,
            emit_event,
            # Decision Engine
            make_decision,
            # Transcription (AssemblyAI)
            transcribe_audio,
            get_transcript,
            # LLM Decomposition (OpenAI)
            decompose_creative,
            validate_decomposition,
            # Hypothesis Generation
            generate_hypotheses,
            save_hypotheses,
            # Telegram Delivery
            send_hypothesis_to_telegram,
            get_buyer_chat_id,
            update_hypothesis_delivery_status,
            emit_delivery_event,
        ],
    )

    # Metrics Worker (Keitaro + Metrics + Learning + Recommendations)
    metrics_worker = Worker(
        client,
        task_queue=settings.temporal.TASK_QUEUE_METRICS,
        workflows=[
            KeitaroPollerWorkflow,
            MetricsProcessingWorkflow,
            LearningLoopWorkflow,
            DailyRecommendationWorkflow,
            SingleRecommendationDeliveryWorkflow,
            MaintenanceWorkflow,
        ],
        activities=[
            # Keitaro activities
            get_all_trackers,
            get_tracker_metrics,
            get_batch_metrics,
            # Metrics activities
            upsert_raw_metrics,
            create_daily_snapshot,
            check_snapshot_exists,
            process_outcome,
            get_unprocessed_snapshots,
            emit_metrics_event,
            # Learning activities
            process_learning_batch,
            get_unprocessed_outcomes,
            process_single_outcome,
            check_death_conditions,
            emit_learning_event,
            # Recommendation activities
            get_active_buyers,
            generate_recommendation_for_buyer,
            send_recommendation_to_telegram,
            update_recommendation_delivery,
            emit_recommendation_event,
            get_recommendation_by_id,
            check_existing_daily_recommendation,
            # Maintenance activities
            reset_stale_buyer_states,
            expire_old_recommendations,
            check_data_integrity,
            emit_maintenance_event,
        ],
    )

    logger.info("Workers configured:")
    logger.info(f"  - Creative Pipeline: {settings.temporal.TASK_QUEUE_CREATIVE_PIPELINE}")
    logger.info(f"  - Metrics & Learning: {settings.temporal.TASK_QUEUE_METRICS}")

    # Run all workers concurrently
    await asyncio.gather(
        creative_worker.run(),
        metrics_worker.run(),
    )


def main():
    """Main entry point."""
    try:
        asyncio.run(run_all_workers())
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
    except Exception as e:
        logger.error(f"Worker error: {e}")
        raise


if __name__ == "__main__":
    main()
