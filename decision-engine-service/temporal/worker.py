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
from temporal.workflows.health_check import HealthCheckWorkflow
from temporal.workflows.buyer_onboarding import BuyerOnboardingWorkflow
from temporal.workflows.historical_import import (
    HistoricalImportWorkflow,
    CreativeRegistrationWorkflow,
    HistoricalVideoHandlerWorkflow,
)
from temporal.workflows.knowledge_ingestion import KnowledgeIngestionWorkflow
from temporal.workflows.knowledge_application import KnowledgeApplicationWorkflow
from temporal.workflows.premise_extraction import (
    PremiseExtractionWorkflow,
    BatchPremiseExtractionWorkflow,
)
from temporal.workflows.modular_hypothesis import ModularHypothesisWorkflow

# Import activities - Supabase
from temporal.activities.supabase import (
    create_creative,
    create_historical_creative,
    get_creative,
    get_idea,
    check_idea_exists,
    create_idea,
    save_decomposed_creative,
    update_creative_status,
    emit_event,
    save_transcript,
    get_existing_transcript,
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
from temporal.activities.premise_selection import (
    select_premise,
)
from temporal.activities.module_extraction import (
    extract_modules_from_decomposition,
    get_creative_metrics,
    upsert_module,
)
from temporal.activities.modular_generation import (
    check_modular_readiness,
    select_module_combinations,
    synthesize_hypothesis_text,
    save_modular_hypothesis,
    generate_modular_hypotheses,
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
    get_campaigns_by_source,
    get_campaign_creatives,
)

# Import activities - Buyer
from temporal.activities.buyer import (
    create_buyer,
    load_buyer_by_telegram_id,
    load_buyer_by_id,
    update_buyer,
    send_telegram_message,
    queue_historical_import,
    get_pending_imports,
    get_pending_video_campaigns,
    update_import_status,
    get_import_by_campaign_id,
    update_import_with_video,
    log_buyer_interaction,
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

# Import activities - Module Learning (Modular Creative System)
from temporal.activities.module_learning import (
    get_modules_for_creative,
    update_module_stats,
    update_compatibility_stats,
    process_module_learning,
    process_module_learning_batch,
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
    mark_stuck_transcriptions_failed,
    archive_failed_creatives,
    check_data_integrity,
    emit_maintenance_event,
    check_staleness,
    release_orphaned_agent_tasks,
    find_stuck_creatives,
)

# Import activities - Feature Monitoring
from temporal.activities.feature_monitoring import (
    update_feature_correlations,
    detect_feature_drift,
    emit_feature_event,
)

# Import activities - Hygiene (cleanup & health)
from temporal.activities.hygiene_cleanup import (
    run_all_cleanup,
    retry_failed_hypotheses,
    cleanup_exhausted_hypotheses,
)
from temporal.activities.hygiene_health import (
    check_supabase_connection,
    get_table_sizes,
    get_pending_counts,
    send_admin_alert,
    save_hygiene_report,
)

# Import activities - Knowledge Extraction
from temporal.activities.knowledge_extraction import (
    extract_knowledge_from_transcript,
    validate_extraction,
)

# Import activities - Premise Extraction
from temporal.activities.premise_extraction import (
    load_creative_data,
    extract_premises_via_llm,
    upsert_premise_and_learning,
    emit_premise_extraction_event,
)
from temporal.activities.knowledge_db import (
    save_knowledge_source,
    save_pending_extractions,
    mark_source_processed,
    get_pending_extractions,
    get_extraction,
    update_extraction_status,
    apply_premise_knowledge,
    apply_process_rule,
    apply_component_weight,
    apply_creative_attribute,
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
            ModularHypothesisWorkflow,
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
            save_transcript,
            get_existing_transcript,
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
            # Premise Selection
            select_premise,
            # Module Extraction (Modular Creative System)
            extract_modules_from_decomposition,
            get_creative_metrics,
            upsert_module,
            # Modular Hypothesis Generation
            check_modular_readiness,
            select_module_combinations,
            synthesize_hypothesis_text,
            save_modular_hypothesis,
            generate_modular_hypotheses,
            # Telegram Delivery
            send_hypothesis_to_telegram,
            get_buyer_chat_id,
            update_hypothesis_delivery_status,
            emit_delivery_event,
        ],
    )

    logger.info(
        f"Starting worker on queue: {settings.temporal.TASK_QUEUE_CREATIVE_PIPELINE}"
    )
    logger.info(
        "Registered workflows: CreativePipelineWorkflow, ModularHypothesisWorkflow"
    )
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
        workflows=[CreativePipelineWorkflow, ModularHypothesisWorkflow],
        activities=[
            # Supabase activities
            get_creative,
            get_idea,
            check_idea_exists,
            create_idea,
            save_decomposed_creative,
            update_creative_status,
            emit_event,
            save_transcript,
            get_existing_transcript,
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
            # Premise Selection
            select_premise,
            # Module Extraction (Modular Creative System)
            extract_modules_from_decomposition,
            get_creative_metrics,
            upsert_module,
            # Modular Hypothesis Generation
            check_modular_readiness,
            select_module_combinations,
            synthesize_hypothesis_text,
            save_modular_hypothesis,
            generate_modular_hypotheses,
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
            HealthCheckWorkflow,
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
            # Module learning activities (Modular Creative System)
            get_modules_for_creative,
            update_module_stats,
            update_compatibility_stats,
            process_module_learning,
            process_module_learning_batch,
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
            mark_stuck_transcriptions_failed,
            archive_failed_creatives,
            check_data_integrity,
            emit_maintenance_event,
            check_staleness,
            release_orphaned_agent_tasks,
            find_stuck_creatives,
            # Feature monitoring activities
            update_feature_correlations,
            detect_feature_drift,
            emit_feature_event,
            # Hygiene activities (cleanup & health)
            run_all_cleanup,
            retry_failed_hypotheses,
            cleanup_exhausted_hypotheses,
            check_supabase_connection,
            get_table_sizes,
            get_pending_counts,
            send_admin_alert,
            save_hygiene_report,
        ],
    )

    # Telegram Worker (Buyer Onboarding + Historical Import)
    telegram_worker = Worker(
        client,
        task_queue=settings.temporal.TASK_QUEUE_TELEGRAM,
        workflows=[
            BuyerOnboardingWorkflow,
            HistoricalImportWorkflow,
            CreativeRegistrationWorkflow,
            HistoricalVideoHandlerWorkflow,
        ],
        activities=[
            # Buyer activities
            create_buyer,
            load_buyer_by_telegram_id,
            load_buyer_by_id,
            update_buyer,
            send_telegram_message,
            queue_historical_import,
            get_pending_imports,
            get_pending_video_campaigns,
            update_import_status,
            get_import_by_campaign_id,
            update_import_with_video,
            log_buyer_interaction,
            # Keitaro activities for historical import
            get_campaigns_by_source,
            get_campaign_creatives,
            # Supabase for creative registration and events
            create_creative,
            create_historical_creative,
            emit_event,
        ],
    )

    # Knowledge Worker (Knowledge Extraction & Application)
    knowledge_worker = Worker(
        client,
        task_queue=settings.temporal.TASK_QUEUE_KNOWLEDGE,
        workflows=[
            KnowledgeIngestionWorkflow,
            KnowledgeApplicationWorkflow,
            PremiseExtractionWorkflow,
            BatchPremiseExtractionWorkflow,
        ],
        activities=[
            # Knowledge extraction (LLM)
            extract_knowledge_from_transcript,
            validate_extraction,
            # Knowledge DB operations
            save_knowledge_source,
            save_pending_extractions,
            mark_source_processed,
            get_pending_extractions,
            get_extraction,
            update_extraction_status,
            # Knowledge application
            apply_premise_knowledge,
            apply_process_rule,
            apply_component_weight,
            apply_creative_attribute,
            # Premise extraction activities
            load_creative_data,
            extract_premises_via_llm,
            upsert_premise_and_learning,
            emit_premise_extraction_event,
            # Telegram (for notifications)
            send_telegram_message,
        ],
    )

    logger.info("Workers configured:")
    logger.info(
        f"  - Creative Pipeline: {settings.temporal.TASK_QUEUE_CREATIVE_PIPELINE}"
    )
    logger.info(f"  - Metrics & Learning: {settings.temporal.TASK_QUEUE_METRICS}")
    logger.info(f"  - Telegram & Buyer: {settings.temporal.TASK_QUEUE_TELEGRAM}")
    logger.info(f"  - Knowledge Extraction: {settings.temporal.TASK_QUEUE_KNOWLEDGE}")

    # Run all workers concurrently
    await asyncio.gather(
        creative_worker.run(),
        metrics_worker.run(),
        telegram_worker.run(),
        knowledge_worker.run(),
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
