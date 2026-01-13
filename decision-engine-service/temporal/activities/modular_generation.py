"""
Modular Hypothesis Generation Activity

Temporal activity for generating hypotheses by combining top-performing modules.
Uses 90/10 exploitation/exploration split for module selection.
LLM synthesizes coherent ad text from selected hook, promise, proof modules.

Part of Modular Creative System (Phase 3).
"""

import os
import json
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any, cast
from temporalio import activity
from temporalio.exceptions import ApplicationError

# Import module selector service
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
from src.core.http_client import get_http_client
from services.module_selector import (
    check_modular_generation_ready,
    select_top_combinations,
)

# Fixed prompt version for reproducibility
PROMPT_VERSION = "modular_v1"

# Fixed temperature for generation
TEMPERATURE = 0.7

# Schema name
SCHEMA = "genomai"

# System prompt for modular synthesis
MODULAR_SYNTHESIS_PROMPT = """You are a creative text synthesizer. Your job is to create a coherent ad text from separate structural components (hook, promise, proof).

## INPUT COMPONENTS:

### Hook (Attention-grabber)
The hook stops the scroll. It should be the opening of the ad.
{hook_content}

### Promise (Value proposition)
The promise tells what the audience will gain.
{promise_content}

### Proof (Credibility)
The proof provides evidence and builds trust.
{proof_content}

## RULES:
1. Create a single, cohesive ad text that flows naturally
2. Preserve the essence of each component
3. The hook MUST come first
4. Blend components seamlessly - no obvious breaks
5. Keep the emotional tone consistent
6. Do NOT add new claims not present in the components
7. Do NOT explain your choices

## OUTPUT FORMAT:
Return a JSON object with a single "text" field containing the synthesized ad.

Example output:
{{
  "text": "The complete synthesized ad text here..."
}}"""


def _get_credentials() -> tuple:
    """Get Supabase credentials from environment."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        raise RuntimeError("Missing Supabase credentials")

    rest_url = f"{supabase_url}/rest/v1"
    return rest_url, supabase_key


def _get_headers(supabase_key: str, for_write: bool = False) -> dict:
    """Get headers for Supabase REST API with genomai schema."""
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Accept-Profile": SCHEMA,
        "Content-Type": "application/json",
    }
    if for_write:
        headers["Content-Profile"] = SCHEMA
        headers["Prefer"] = "return=representation"
    return headers


def _format_module_content(module: Dict[str, Any]) -> str:
    """
    Format module content for LLM prompt.

    Args:
        module: Module dict with content and text_content

    Returns:
        Formatted string for prompt
    """
    parts = []

    # Add text content if available (for hooks)
    if module.get("text_content"):
        parts.append(f"Text: {module['text_content']}")

    # Add structured content
    content = module.get("content", {})
    if isinstance(content, str):
        try:
            content = json.loads(content)
        except json.JSONDecodeError:
            content = {}

    for key, value in content.items():
        if value is not None:
            if isinstance(value, list):
                parts.append(f"{key}: {', '.join(str(v) for v in value)}")
            else:
                parts.append(f"{key}: {value}")

    return "\n".join(parts) if parts else "No content available"


@activity.defn
async def check_modular_readiness(
    vertical: Optional[str] = None,
    geo: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Check if modular generation is ready.

    Args:
        vertical: Optional filter by vertical
        geo: Optional filter by GEO

    Returns:
        Readiness status dict
    """
    return cast(Dict[str, Any], await check_modular_generation_ready(vertical, geo))


@activity.defn
async def select_module_combinations(
    count: int = 3,
    vertical: Optional[str] = None,
    geo: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Select module combinations for hypothesis generation.

    Args:
        count: Number of combinations to select
        vertical: Optional filter by vertical
        geo: Optional filter by GEO

    Returns:
        List of module combinations
    """
    return cast(List[Dict[str, Any]], await select_top_combinations(count, vertical, geo))


@activity.defn
async def synthesize_hypothesis_text(
    hook: Dict[str, Any],
    promise: Dict[str, Any],
    proof: Dict[str, Any],
) -> str:
    """
    Use LLM to synthesize coherent ad text from modules.

    Args:
        hook: Hook module dict
        promise: Promise module dict
        proof: Proof module dict

    Returns:
        Synthesized ad text
    """
    import openai

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ApplicationError("OPENAI_API_KEY not configured")

    client = openai.OpenAI(api_key=api_key)

    # Format module contents
    hook_content = _format_module_content(hook)
    promise_content = _format_module_content(promise)
    proof_content = _format_module_content(proof)

    prompt = MODULAR_SYNTHESIS_PROMPT.format(
        hook_content=hook_content,
        promise_content=promise_content,
        proof_content=proof_content,
    )

    activity.logger.info(
        f"Synthesizing hypothesis from modules: "
        f"hook={hook['id']}, promise={promise['id']}, proof={proof['id']}"
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": "Create the synthesized ad text."},
            ],
            temperature=TEMPERATURE,
            max_tokens=2000,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        if not content:
            raise ApplicationError("LLM returned empty response", type="LLM_ERROR")

        # Parse JSON
        try:
            result = json.loads(content)
        except json.JSONDecodeError as e:
            raise ApplicationError(f"LLM returned invalid JSON: {e}", type="SCHEMA_ERROR") from e

        # Validate structure
        if "text" not in result:
            raise ApplicationError("LLM response missing 'text' field", type="SCHEMA_ERROR")

        synthesized_text = cast(str, result["text"])
        activity.logger.info(f"Synthesized text length: {len(synthesized_text)}")

        return synthesized_text

    except openai.APIError as e:
        raise ApplicationError(f"OpenAI API error: {e}", type="LLM_API_ERROR") from e


@activity.defn
async def save_modular_hypothesis(
    content: str,
    idea_id: str,
    decision_id: str,
    hook_module_id: str,
    promise_module_id: str,
    proof_module_id: str,
    buyer_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Save modular hypothesis to database.

    Modular hypotheses are created with:
    - generation_mode = 'modular'
    - review_status = 'pending_review' (requires human approval)
    - module references (hook_module_id, promise_module_id, proof_module_id)

    Args:
        content: Synthesized hypothesis text
        idea_id: Idea UUID
        decision_id: Decision UUID
        hook_module_id: Hook module UUID
        promise_module_id: Promise module UUID
        proof_module_id: Proof module UUID
        buyer_id: Optional buyer UUID

    Returns:
        Created hypothesis record
    """

    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key, for_write=True)

    now = datetime.utcnow().isoformat()

    hypothesis = {
        "id": str(uuid.uuid4()),
        "idea_id": idea_id,
        "decision_id": decision_id,
        "content": content,
        "prompt_version": PROMPT_VERSION,
        "created_at": now,
        "generation_mode": "modular",
        "review_status": "pending_review",
        "hook_module_id": hook_module_id,
        "promise_module_id": promise_module_id,
        "proof_module_id": proof_module_id,
    }

    if buyer_id:
        hypothesis["buyer_id"] = buyer_id

    client = get_http_client()
    response = await client.post(
        f"{rest_url}/hypotheses",
        headers=headers,
        json=hypothesis,
    )
    response.raise_for_status()
    data = cast(List[Dict[str, Any]], response.json())

    if not data:
        raise ApplicationError("Failed to insert hypothesis: no data returned")

    activity.logger.info(
        f"Saved modular hypothesis {data[0]['id']} "
        f"(hook={hook_module_id}, promise={promise_module_id}, proof={proof_module_id})"
    )

    return data[0]


@activity.defn
async def generate_modular_hypotheses(
    idea_id: str,
    decision_id: str,
    count: int = 3,
    vertical: Optional[str] = None,
    geo: Optional[str] = None,
    buyer_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate hypotheses using modular combination approach.

    Main activity for modular hypothesis generation.

    Algorithm:
    1. Check if enough modules exist
    2. Select top module combinations (90/10 split)
    3. LLM synthesizes each combination into coherent text
    4. Save hypotheses with module references

    Args:
        idea_id: Idea UUID
        decision_id: Decision UUID
        count: Number of hypotheses to generate
        vertical: Optional filter by vertical
        geo: Optional filter by GEO
        buyer_id: Optional buyer UUID

    Returns:
        Dict with:
            - hypotheses: List of created hypothesis records
            - count: Number of hypotheses generated
            - generation_mode: 'modular'
            - combinations: Module combinations used
    """
    activity.logger.info(f"Starting modular generation for idea={idea_id}, count={count}")

    # 1. Check readiness
    readiness = await check_modular_generation_ready(vertical, geo)
    if not readiness["ready"]:
        activity.logger.warning(f"Modular generation not ready: {readiness['reason']}")
        return {
            "hypotheses": [],
            "count": 0,
            "generation_mode": "modular",
            "combinations": [],
            "error": readiness["reason"],
        }

    # 2. Select module combinations
    combinations = await select_top_combinations(count, vertical, geo)

    if not combinations:
        activity.logger.warning("No module combinations available")
        return {
            "hypotheses": [],
            "count": 0,
            "generation_mode": "modular",
            "combinations": [],
            "error": "No module combinations available",
        }

    activity.logger.info(f"Selected {len(combinations)} module combinations")

    # 3. Synthesize and save hypotheses
    created_hypotheses = []
    combination_details = []

    for combo in combinations:
        try:
            # Synthesize text
            synthesized_text = await synthesize_hypothesis_text(
                hook=combo["hook"],
                promise=combo["promise"],
                proof=combo["proof"],
            )

            # Save hypothesis
            hypothesis = await save_modular_hypothesis(
                content=synthesized_text,
                idea_id=idea_id,
                decision_id=decision_id,
                hook_module_id=combo["hook"]["id"],
                promise_module_id=combo["promise"]["id"],
                proof_module_id=combo["proof"]["id"],
                buyer_id=buyer_id,
            )

            created_hypotheses.append(hypothesis)
            combination_details.append(
                {
                    "hook_id": combo["hook"]["id"],
                    "promise_id": combo["promise"]["id"],
                    "proof_id": combo["proof"]["id"],
                    "combined_score": combo.get("combined_score", 0),
                }
            )

        except Exception as e:
            activity.logger.error(f"Failed to generate hypothesis from combination: {e}")
            continue

    activity.logger.info(
        f"Generated {len(created_hypotheses)} modular hypotheses for idea={idea_id}"
    )

    return {
        "hypotheses": created_hypotheses,
        "count": len(created_hypotheses),
        "generation_mode": "modular",
        "combinations": combination_details,
    }
