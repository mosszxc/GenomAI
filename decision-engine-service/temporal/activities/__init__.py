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
]
