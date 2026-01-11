"""
Knowledge Extraction Activity

Temporal activity for extracting structured knowledge from training transcripts.
Extracts premises, creative attributes, process rules, and component weights.

The LLM acts as a CLASSIFIER only - no evaluation, no scoring, no quality judgment.
"""

import os
import json
from typing import Optional
from temporalio import activity
from temporalio.exceptions import ApplicationError


# System prompt for knowledge extraction
KNOWLEDGE_EXTRACTION_PROMPT = """You are a knowledge extractor for a creative advertising system.

Your task is to analyze training transcripts from expert copywriters and extract actionable knowledge.

## KNOWLEDGE TYPES TO EXTRACT:

1. **premise**: Narrative story patterns for advertising
   - Look for: origin stories, discovery narratives, confession patterns, unique mechanisms
   - Types: method, discovery, confession, secret, ingredient, mechanism, breakthrough, transformation
   - Output: premise_type, name, origin_story, mechanism_claim

2. **creative_attribute**: New values for creative classification fields
   - Look for: new hook types, new emotional triggers, new proof structures
   - Only extract if it's a NEW enum value not in existing list
   - Output: field_name, value, description

3. **process_rule**: Best practices for creative construction
   - Look for: "always do X before Y", "never do X without Y", structural recommendations
   - Output: rule_name, condition, recommendation, applies_to

4. **component_weight**: Expert opinions on what works together
   - Look for: "X combined with Y works well", correlations between elements
   - Output: component_type, component_value, correlations, suggested_boost

## EXISTING SCHEMA FIELDS (for creative_attribute - only extract NEW values):
- angle_type: pain, fear, hope, curiosity, authority, social_proof, urgency, identity
- hook_mechanism: pattern_interrupt, counter_intuitive, specific_number, confession, direct_question, shock_statement
- proof_type: personal_story, expert_quote, research, testimonial, statistics, demonstration
- story_type: direct, parallel, discovery, confession, transformation
- ump_type: hidden_cause, wrong_approach, missing_ingredient, inflammation, absorption
- ums_type: secret_ingredient, new_technology, natural_approach, scientific_method
- paradigm_shift_type: blame_shift, new_understanding, revelation, myth_bust
- cta_style: direct, two_step, soft, embedded
- emotion_primary: fear, relief, anger, hope, curiosity, shame, trust
- promise_type: instant, gradual, effortless, hidden, scientific, guaranteed, preventive

## RULES:
1. Extract ONLY structured knowledge, not opinions or vague statements
2. Include supporting quotes from transcript (verbatim excerpts)
3. Assign confidence_score based on clarity of the teaching (0.0-1.0)
4. Skip if similar to existing enum values above
5. Each extraction must be actionable and concrete

## OUTPUT FORMAT:
Return JSON object with "extractions" array:
{
  "extractions": [
    {
      "knowledge_type": "premise",
      "name": "The 72-Hour Reset",
      "description": "A method premise based on time-boxed intervention",
      "payload": {
        "premise_type": "method",
        "name": "The 72-Hour Reset",
        "origin_story": "Discovered accidentally when patient missed appointments...",
        "mechanism_claim": "Triggers hormetic stress response in the body"
      },
      "confidence_score": 0.85,
      "supporting_quotes": ["In just 72 hours, the body begins to...", "I discovered this when..."]
    }
  ]
}

If no actionable knowledge found, return: {"extractions": []}
"""


def chunk_transcript(text: str, max_chars: int = 12000) -> list[str]:
    """
    Split long transcript into chunks for processing.

    Uses paragraph boundaries to avoid splitting mid-sentence.
    """
    if len(text) <= max_chars:
        return [text]

    chunks = []
    paragraphs = text.split('\n\n')
    current_chunk = ""

    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 > max_chars:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = para
        else:
            current_chunk = current_chunk + "\n\n" + para if current_chunk else para

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks


def deduplicate_extractions(extractions: list[dict]) -> list[dict]:
    """
    Remove duplicate extractions based on name and type.
    """
    seen = set()
    unique = []

    for ext in extractions:
        key = (ext.get("knowledge_type"), ext.get("name", "").lower().strip())
        if key not in seen:
            seen.add(key)
            unique.append(ext)

    return unique


@activity.defn
async def extract_knowledge_from_transcript(
    transcript_text: str,
    source_id: Optional[str] = None,
    title: Optional[str] = None,
) -> dict:
    """
    Extract structured knowledge from training transcript using LLM.

    The LLM acts as a classifier only - no evaluation, no scoring.

    Args:
        transcript_text: Full transcript text from training video
        source_id: Optional source ID for logging
        title: Optional title for context

    Returns:
        dict with:
            - extractions: List of extracted knowledge items
            - chunk_count: Number of chunks processed
            - total_extracted: Total number of extractions

    Raises:
        ApplicationError: If LLM returns invalid response or API fails
    """
    import openai

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ApplicationError("OPENAI_API_KEY not configured")

    client = openai.OpenAI(api_key=api_key)

    activity.logger.info(
        f"Extracting knowledge from: {title or source_id or 'unknown'}, "
        f"length={len(transcript_text)}"
    )

    # Chunk transcript if too long
    chunks = chunk_transcript(transcript_text)
    activity.logger.info(f"Processing {len(chunks)} chunk(s)")

    all_extractions = []

    for i, chunk in enumerate(chunks):
        activity.logger.info(f"Processing chunk {i+1}/{len(chunks)}")

        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": KNOWLEDGE_EXTRACTION_PROMPT},
                    {"role": "user", "content": f"Title: {title or 'Training Video'}\n\nTranscript:\n{chunk}"},
                ],
                temperature=0.3,  # Low temperature for consistent extraction
                max_tokens=4000,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            if not content:
                activity.logger.warning(f"Empty response for chunk {i+1}")
                continue

            # Parse JSON
            try:
                result = json.loads(content)
                extractions = result.get("extractions", [])
                all_extractions.extend(extractions)
                activity.logger.info(f"Chunk {i+1}: extracted {len(extractions)} items")
            except json.JSONDecodeError as e:
                activity.logger.error(f"Invalid JSON in chunk {i+1}: {e}")
                continue

        except openai.APIError as e:
            activity.logger.error(f"OpenAI API error in chunk {i+1}: {e}")
            continue

    # Deduplicate across chunks
    unique_extractions = deduplicate_extractions(all_extractions)

    activity.logger.info(
        f"Extraction complete: {len(unique_extractions)} unique items "
        f"from {len(all_extractions)} total"
    )

    return {
        "extractions": unique_extractions,
        "chunk_count": len(chunks),
        "total_extracted": len(unique_extractions),
    }


@activity.defn
async def validate_extraction(extraction: dict) -> dict:
    """
    Validate single extraction against expected schema.

    Args:
        extraction: Single extraction dict

    Returns:
        dict with is_valid and errors list
    """
    errors = []

    # Required fields
    required = ["knowledge_type", "name", "payload"]
    for field in required:
        if field not in extraction:
            errors.append(f"Missing required field: {field}")

    # Validate knowledge_type
    valid_types = ["premise", "creative_attribute", "process_rule", "component_weight"]
    if extraction.get("knowledge_type") not in valid_types:
        errors.append(f"Invalid knowledge_type: {extraction.get('knowledge_type')}")

    # Validate confidence_score if present
    score = extraction.get("confidence_score")
    if score is not None:
        if not isinstance(score, (int, float)) or score < 0 or score > 1:
            errors.append(f"Invalid confidence_score: {score}")

    # Validate payload based on type
    payload = extraction.get("payload", {})
    knowledge_type = extraction.get("knowledge_type")

    if knowledge_type == "premise":
        if not payload.get("premise_type"):
            errors.append("premise payload missing premise_type")
        if not payload.get("name"):
            errors.append("premise payload missing name")

    elif knowledge_type == "creative_attribute":
        if not payload.get("field_name"):
            errors.append("creative_attribute payload missing field_name")
        if not payload.get("value"):
            errors.append("creative_attribute payload missing value")

    elif knowledge_type == "process_rule":
        if not payload.get("rule_name"):
            errors.append("process_rule payload missing rule_name")
        if not payload.get("recommendation"):
            errors.append("process_rule payload missing recommendation")

    elif knowledge_type == "component_weight":
        if not payload.get("component_type"):
            errors.append("component_weight payload missing component_type")
        if not payload.get("component_value"):
            errors.append("component_weight payload missing component_value")

    return {
        "is_valid": len(errors) == 0,
        "errors": errors,
    }
