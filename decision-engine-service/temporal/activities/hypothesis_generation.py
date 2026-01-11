"""
Hypothesis Generation Activity

Temporal activity for generating text hypotheses using LLM.
Converts approved ideas into 1-3 text variations for testing.

The LLM generates variations only - NO evaluation, NO ranking, NO scoring.
"""

import os
import json
import uuid
from datetime import datetime
from typing import Optional, List
from temporalio import activity
from temporalio.exceptions import ApplicationError

# Fixed prompt version for reproducibility
# v4: Added variables denormalization from decomposed_creatives
PROMPT_VERSION = "v4"

# Number of hypotheses to generate
NUM_HYPOTHESES = 3

# Fixed temperature for generation
TEMPERATURE = 0.7

# System prompt for hypothesis generation
HYPOTHESIS_SYSTEM_PROMPT = """You are a creative text generator. Your job is to generate text variations based on the provided creative structure.

## RULES:
1. Generate exactly {num_hypotheses} distinct text variations
2. Each variation should be a complete, standalone ad text
3. Maintain the core message and structure from the input
4. Do NOT evaluate or compare the variations
5. Do NOT explain your choices
6. Do NOT add metadata or commentary

## OUTPUT FORMAT:
Return a JSON object with a "hypotheses" array containing {num_hypotheses} strings.
Each string is a complete ad text variation.

Example output:
{{
  "hypotheses": [
    "First variation text here...",
    "Second variation text here...",
    "Third variation text here..."
  ]
}}"""


@activity.defn
async def generate_hypotheses(
    idea_id: str,
    decision_id: str,
    decomposed_payload: dict,
    num_hypotheses: int = NUM_HYPOTHESES,
) -> dict:
    """
    Generate text hypotheses from decomposed creative.

    Only called for APPROVED decisions.

    Args:
        idea_id: Idea UUID
        decision_id: Decision UUID that approved this idea
        decomposed_payload: Canonical Schema v2 payload
        num_hypotheses: Number of variations to generate (default: 3)

    Returns:
        dict with:
            - hypotheses: List of generated text variations
            - prompt_version: Version of prompt used
            - count: Number of hypotheses generated

    Raises:
        ApplicationError: If LLM fails or returns invalid format
    """
    import openai

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ApplicationError("OPENAI_API_KEY not configured")

    client = openai.OpenAI(api_key=api_key)

    activity.logger.info(
        f"Generating {num_hypotheses} hypotheses for idea={idea_id}, decision={decision_id}"
    )

    # Build user prompt from decomposed payload
    user_prompt = _build_generation_prompt(decomposed_payload)

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": HYPOTHESIS_SYSTEM_PROMPT.format(
                        num_hypotheses=num_hypotheses
                    ),
                },
                {"role": "user", "content": user_prompt},
            ],
            temperature=TEMPERATURE,
            max_tokens=4000,
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
            result = json.loads(content)
        except json.JSONDecodeError as e:
            raise ApplicationError(
                f"LLM returned invalid JSON: {e}",
                type="SCHEMA_ERROR",
            )

        # Validate structure
        if "hypotheses" not in result:
            raise ApplicationError(
                "LLM response missing 'hypotheses' field",
                type="SCHEMA_ERROR",
            )

        hypotheses = result["hypotheses"]
        if not isinstance(hypotheses, list) or len(hypotheses) == 0:
            raise ApplicationError(
                "LLM returned empty or invalid hypotheses list",
                type="SCHEMA_ERROR",
            )

        activity.logger.info(
            f"Generated {len(hypotheses)} hypotheses for idea={idea_id}"
        )

        return {
            "hypotheses": hypotheses,
            "prompt_version": PROMPT_VERSION,
            "count": len(hypotheses),
            "idea_id": idea_id,
            "decision_id": decision_id,
        }

    except openai.APIError as e:
        raise ApplicationError(
            f"OpenAI API error: {e}",
            type="LLM_API_ERROR",
        )


def _build_generation_prompt(payload: dict) -> str:
    """
    Build user prompt from decomposed payload.

    Deterministic: same payload -> same prompt.
    """
    parts = [
        "Generate ad text variations based on this creative structure:",
        "",
        f"Angle: {payload.get('angle_type', 'unknown')}",
        f"Core Belief: {payload.get('core_belief', 'unknown')}",
        f"Promise Type: {payload.get('promise_type', 'unknown')}",
        f"Primary Emotion: {payload.get('emotion_primary', 'unknown')}",
        f"Emotion Intensity: {payload.get('emotion_intensity', 'unknown')}",
        f"Message Structure: {payload.get('message_structure', 'unknown')}",
        f"Opening Type: {payload.get('opening_type', 'unknown')}",
        f"State Before: {payload.get('state_before', 'unknown')}",
        f"State After: {payload.get('state_after', 'unknown')}",
        f"Context Frame: {payload.get('context_frame', 'unknown')}",
    ]

    # Add optional fields if present
    if payload.get("ump_present"):
        parts.append(f"UMP Type: {payload.get('ump_type', 'none')}")

    if payload.get("ums_present"):
        parts.append(f"UMS Type: {payload.get('ums_type', 'none')}")

    if payload.get("hook_mechanism"):
        parts.append(f"Hook Mechanism: {payload.get('hook_mechanism')}")

    if payload.get("story_type"):
        parts.append(f"Story Type: {payload.get('story_type')}")

    if payload.get("cta_style"):
        parts.append(f"CTA Style: {payload.get('cta_style')}")

    return "\n".join(parts)


@activity.defn
async def save_hypotheses(
    hypotheses: List[str],
    idea_id: str,
    decision_id: str,
    prompt_version: str,
    variables: Optional[dict] = None,
    buyer_id: Optional[str] = None,
    premise_id: Optional[str] = None,
) -> List[dict]:
    """
    Save generated hypotheses to Supabase.

    Args:
        hypotheses: List of generated text variations
        idea_id: Idea UUID
        decision_id: Decision UUID
        prompt_version: Version of prompt used
        variables: Decomposed payload variables for denormalization
        buyer_id: Buyer UUID for delivery routing
        premise_id: Premise UUID that hypothesis is based on (from premise selector)

    Returns:
        List of created hypothesis records
    """
    import httpx

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        raise ApplicationError("Supabase credentials not configured")

    rest_url = f"{supabase_url}/rest/v1"
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Accept-Profile": "genomai",
        "Content-Profile": "genomai",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

    created_hypotheses = []
    now = datetime.utcnow().isoformat()

    async with httpx.AsyncClient() as client:
        for content in hypotheses:
            hypothesis = {
                "id": str(uuid.uuid4()),
                "idea_id": idea_id,
                "decision_id": decision_id,
                "prompt_version": prompt_version,
                "content": content,
                "created_at": now,
                "variables": variables,
                "buyer_id": buyer_id,
                "premise_id": premise_id,
            }

            response = await client.post(
                f"{rest_url}/hypotheses",
                headers=headers,
                json=hypothesis,
            )
            response.raise_for_status()
            data = response.json()

            if data:
                created_hypotheses.append(data[0])

    activity.logger.info(
        f"Saved {len(created_hypotheses)} hypotheses for idea={idea_id}"
    )

    return created_hypotheses
