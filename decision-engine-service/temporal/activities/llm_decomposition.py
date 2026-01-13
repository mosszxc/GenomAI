"""
LLM Decomposition Activity

Temporal activity for creative decomposition using OpenAI.
Converts transcript text into structured Canonical Schema v2 format.

The LLM acts as a CLASSIFIER only - no evaluation, no scoring, no quality judgment.
"""

import os
import json
import hashlib
from typing import Optional
from temporalio import activity
from temporalio.exceptions import ApplicationError

# Schema version for decomposition
SCHEMA_VERSION = "v2"

# System prompt for LLM classification (from 02_decomposition_playbook.md)
DECOMPOSITION_SYSTEM_PROMPT = """You are a creative classifier. Your ONLY job is to analyze the transcript and fill fields according to the schema.

## RULES:
1. You are NOT an evaluator. You do NOT judge quality.
2. Fill ONLY schema fields. NEVER add extra fields.
3. If unsure, use the closest enum value.
4. Boolean fields: true/false based on evidence in text.
5. Array fields: include all matching markers found.

## OUTPUT FORMAT:
Return ONLY valid JSON. No explanation. No markdown.

## V1 REQUIRED FIELDS (always fill):
- angle_type: Primary message angle (pain/fear/hope/curiosity/authority/social_proof/urgency/identity)
- core_belief: Core belief communicated (problem_is_serious/problem_is_hidden/solution_is_simple/solution_is_safe/solution_is_scientific/solution_is_unknown/others_have_this_problem/doctors_are_wrong/time_is_running_out)
- promise_type: Type of promise (instant/gradual/effortless/hidden/scientific/guaranteed/preventive)
- emotion_primary: Primary emotion evoked (fear/relief/anger/hope/curiosity/shame/trust)
- emotion_intensity: Intensity level (low/medium/high)
- message_structure: Message structure (problem_solution/story_reveal/myth_debunk/authority_proof/question_answer/before_after/confession)
- opening_type: Opening type (shock_statement/direct_question/personal_story/authority_claim/visual_pattern_break)
- state_before: State before solution (unsafe/uncertain/powerless/ignorant/overwhelmed/excluded/dissatisfied)
- state_after: State after solution (safe/confident/in_control/informed/calm/included/satisfied)
- context_frame: Contextual framing (institutional/anti_authority/peer_based/expert_led/personal_confession/ironic)
- source_type: always "internal" for system-generated
- risk_level: Risk level (low/medium/high)
- horizon: Time horizon (T1/T2/T3)
- schema_version: always "v2"

## V2 OPTIONAL FIELDS (fill when evidence present):

### UMP/UMS (Unique Mechanism)
- ump_present (boolean): Is there a hidden reason for failure explained?
- ump_type: Type of hidden problem (hidden_cause/wrong_approach/missing_ingredient/inflammation/absorption/none)
- ums_present (boolean): Is there a unique solution mechanism?
- ums_type: Type of solution (secret_ingredient/new_technology/natural_approach/scientific_method/none)

### Paradigm Shift
- paradigm_shift_present (boolean): Does the ad change beliefs?
- paradigm_shift_type: Type of shift (blame_shift/new_understanding/revelation/myth_bust/none)

### Specificity
- specificity_level: How specific is the copy? (high/medium/low)
- specificity_markers (array): Types of specific details found (money_amount/time_period/product_names/person_names/locations/statistics)

### Hook
- hook_mechanism: How does the hook stop the scroll? (pattern_interrupt/counter_intuitive/specific_number/confession/direct_question/shock_statement)
- hook_stopping_power (high/medium/low): Estimated scroll-stopping power

### Proof
- proof_type: Primary proof type (personal_story/expert_quote/research/testimonial/statistics/demonstration)
- proof_source: Who provides credibility (self/expert/doctor/research_institution/customer/celebrity)

### Story
- story_type: Story structure used (direct/parallel/discovery/confession/transformation)
- story_bridge_present (boolean): Is there a bridge connecting problem to solution?

### Desire
- desire_level: Is it addressing surface or deep desire? (surface/deep)
- emotional_trigger: Primary trigger (fear_of_loss/shame/social_rejection/health_anxiety/relationship_fear/aging_fear/financial_fear)

### Social Proof
- social_proof_pattern: How is social proof presented? (single/cascading/stacked)
- proof_progression: Timeline of results shown (immediate/short_term/long_term/multi_stage)

### CTA
- cta_style: Call-to-action style (direct/two_step/soft/embedded)
- risk_reversal_type: Risk reversal offered (money_back/performance_guarantee/keep_bonus/none)

### Focus (Rule of One)
- focus_score: Is copy focused or scattered? (focused/scattered)
- idea_count (1/2/3): Number of distinct ideas in copy
- emotion_count (1/2/3): Number of distinct emotions targeted"""


# Required fields for schema validation
REQUIRED_FIELDS = [
    "angle_type",
    "core_belief",
    "promise_type",
    "emotion_primary",
    "emotion_intensity",
    "message_structure",
    "opening_type",
    "state_before",
    "state_after",
    "context_frame",
    "source_type",
    "risk_level",
    "horizon",
    "schema_version",
]


@activity.defn
async def decompose_creative(
    transcript_text: str,
    creative_id: Optional[str] = None,
) -> dict:
    """
    Decompose creative transcript into structured schema using LLM.

    The LLM acts as a classifier only - no evaluation, no scoring.

    Args:
        transcript_text: Full transcript text from video
        creative_id: Optional creative ID for logging

    Returns:
        dict with:
            - payload: Decomposed creative (Canonical Schema v2)
            - canonical_hash: SHA256 hash for deduplication
            - schema_version: "v2"

    Raises:
        ApplicationError: If LLM returns invalid schema or API fails
    """
    import openai

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ApplicationError("OPENAI_API_KEY not configured")

    client = openai.OpenAI(api_key=api_key)

    activity.logger.info(
        f"Decomposing creative: {creative_id or 'unknown'}, "
        f"transcript_length={len(transcript_text)}"
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": DECOMPOSITION_SYSTEM_PROMPT},
                {"role": "user", "content": transcript_text},
            ],
            temperature=0.3,  # Low temperature for consistent classification
            max_tokens=2000,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        if not content:
            raise ApplicationError(
                "LLM returned empty response",
                type="LLM_ERROR",
            )

        # Parse JSON
        try:
            payload = json.loads(content)
        except json.JSONDecodeError as e:
            raise ApplicationError(
                f"LLM returned invalid JSON: {e}",
                type="SCHEMA_ERROR",
            ) from e

        # Validate required fields
        missing_fields = [f for f in REQUIRED_FIELDS if f not in payload]
        if missing_fields:
            raise ApplicationError(
                f"Missing required fields: {missing_fields}",
                type="SCHEMA_ERROR",
            )

        # Ensure schema_version is set correctly
        payload["schema_version"] = SCHEMA_VERSION

        # Compute canonical hash for deduplication
        canonical_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode()
        ).hexdigest()

        activity.logger.info(f"Decomposition completed: hash={canonical_hash[:16]}...")

        return {
            "payload": payload,
            "canonical_hash": canonical_hash,
            "schema_version": SCHEMA_VERSION,
        }

    except openai.APIError as e:
        raise ApplicationError(
            f"OpenAI API error: {e}",
            type="LLM_API_ERROR",
        ) from e


@activity.defn
async def validate_decomposition(payload: dict) -> dict:
    """
    Validate decomposition payload against schema.

    Args:
        payload: Decomposed creative payload

    Returns:
        dict with is_valid and errors list

    Note: This is a lightweight validation. Full schema validation
    should be done via JSON Schema in production.
    """
    errors = []

    # Check required fields
    for field in REQUIRED_FIELDS:
        if field not in payload:
            errors.append(f"Missing required field: {field}")

    # Check schema version
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"Invalid schema_version: expected {SCHEMA_VERSION}")

    return {
        "is_valid": len(errors) == 0,
        "errors": errors,
    }
