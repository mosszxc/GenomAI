"""
Temporal Activities

Activity implementations for external calls, DB operations, and service integrations.
Activities are the building blocks of workflows - they perform the actual work.
"""

from temporal.activities.supabase import (
    create_creative,
    get_creative,
    get_idea,
    check_idea_exists,
    create_idea,
    upsert_idea,
    save_decomposed_creative,
    update_creative_status,
    emit_event,
    save_transcript,
    get_existing_transcript,
)
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
from temporal.activities.keitaro import (
    get_all_trackers,
    get_tracker_metrics,
    get_batch_metrics,
    get_campaigns_by_source,
    get_campaign_creatives,
)
from temporal.activities.buyer import (
    create_buyer,
    load_buyer_by_telegram_id,
    load_buyer_by_id,
    update_buyer,
    send_telegram_message,
    queue_historical_import,
    get_pending_imports,
    update_import_status,
)
from temporal.activities.metrics import (
    upsert_raw_metrics,
    create_daily_snapshot,
    check_snapshot_exists,
    process_outcome,
    get_unprocessed_snapshots,
    emit_metrics_event,
)
from temporal.activities.learning import (
    process_learning_batch,
    get_unprocessed_outcomes,
    process_single_outcome,
    check_death_conditions,
    emit_learning_event,
)
from temporal.activities.recommendation import (
    get_active_buyers,
    generate_recommendation_for_buyer,
    send_recommendation_to_telegram,
    update_recommendation_delivery,
    emit_recommendation_event,
    get_recommendation_by_id,
    check_existing_daily_recommendation,
)
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
from temporal.activities.feature_monitoring import (
    update_feature_correlations,
    detect_feature_drift,
    emit_feature_event,
)
from temporal.activities.module_extraction import (
    extract_modules_from_decomposition,
    get_creative_metrics,
    upsert_module,
)
from temporal.activities.module_learning import (
    update_module_stats,
    update_compatibility_stats,
    process_module_learning,
)

__all__ = [
    # Supabase activities
    "create_creative",
    "get_creative",
    "get_idea",
    "check_idea_exists",
    "create_idea",
    "upsert_idea",
    "save_decomposed_creative",
    "update_creative_status",
    "emit_event",
    "save_transcript",
    "get_existing_transcript",
    # Decision Engine
    "make_decision",
    # Transcription (AssemblyAI)
    "transcribe_audio",
    "get_transcript",
    # LLM Decomposition (OpenAI)
    "decompose_creative",
    "validate_decomposition",
    # Hypothesis Generation
    "generate_hypotheses",
    "save_hypotheses",
    # Telegram Delivery
    "send_hypothesis_to_telegram",
    "get_buyer_chat_id",
    "update_hypothesis_delivery_status",
    "emit_delivery_event",
    # Keitaro activities
    "get_all_trackers",
    "get_tracker_metrics",
    "get_batch_metrics",
    "get_campaigns_by_source",
    "get_campaign_creatives",
    # Buyer activities
    "create_buyer",
    "load_buyer_by_telegram_id",
    "load_buyer_by_id",
    "update_buyer",
    "send_telegram_message",
    "queue_historical_import",
    "get_pending_imports",
    "update_import_status",
    # Metrics activities
    "upsert_raw_metrics",
    "create_daily_snapshot",
    "check_snapshot_exists",
    "process_outcome",
    "get_unprocessed_snapshots",
    "emit_metrics_event",
    # Learning activities
    "process_learning_batch",
    "get_unprocessed_outcomes",
    "process_single_outcome",
    "check_death_conditions",
    "emit_learning_event",
    # Recommendation activities
    "get_active_buyers",
    "generate_recommendation_for_buyer",
    "send_recommendation_to_telegram",
    "update_recommendation_delivery",
    "emit_recommendation_event",
    "get_recommendation_by_id",
    "check_existing_daily_recommendation",
    # Maintenance activities
    "reset_stale_buyer_states",
    "expire_old_recommendations",
    "mark_stuck_transcriptions_failed",
    "archive_failed_creatives",
    "check_data_integrity",
    "emit_maintenance_event",
    "check_staleness",
    "release_orphaned_agent_tasks",
    "find_stuck_creatives",
    # Feature monitoring activities
    "update_feature_correlations",
    "detect_feature_drift",
    "emit_feature_event",
    # Module extraction activities
    "extract_modules_from_decomposition",
    "get_creative_metrics",
    "upsert_module",
    # Module learning activities
    "update_module_stats",
    "update_compatibility_stats",
    "process_module_learning",
]
