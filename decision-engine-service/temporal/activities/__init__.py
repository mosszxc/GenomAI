"""
Temporal Activities

Activity implementations for external calls, DB operations, and service integrations.
Activities are the building blocks of workflows - they perform the actual work.
"""

from temporal.activities.supabase import (
    get_creative,
    get_idea,
    check_idea_exists,
    create_idea,
    save_decomposed_creative,
    update_creative_status,
    emit_event,
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
    check_data_integrity,
    emit_maintenance_event,
)

__all__ = [
    # Supabase activities
    "get_creative",
    "get_idea",
    "check_idea_exists",
    "create_idea",
    "save_decomposed_creative",
    "update_creative_status",
    "emit_event",
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
    "check_data_integrity",
    "emit_maintenance_event",
]
