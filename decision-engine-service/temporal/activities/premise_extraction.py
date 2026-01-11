"""
Premise Extraction Activities

Temporal activities for extracting premises from concluded creatives.
Uses creative data + transcript + Keitaro metrics to identify patterns.

Both winning AND losing creatives provide valuable data:
- Winners: successful premise patterns
- Losers: anti-patterns to avoid
"""

import os
import json
from typing import Optional, List
from dataclasses import dataclass
from temporalio import activity
from temporalio.exceptions import ApplicationError
import httpx


SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")


@dataclass
class CreativeData:
    """Aggregated creative data for premise extraction."""

    creative_id: str
    video_url: Optional[str]
    test_result: str  # 'win' or 'loss'
    tracker_id: Optional[str]
    vertical: Optional[str]
    geo: Optional[str]

    # From decomposed_creatives
    payload: Optional[dict]

    # From transcripts
    transcript_text: Optional[str]

    # Metrics
    spend: float
    revenue: float
    cpa: Optional[float]
    roi: Optional[float]


@dataclass
class ExtractedPremise:
    """Single premise extracted from creative."""

    premise_type: str
    name: str
    origin_story: Optional[str]
    mechanism_claim: Optional[str]
    confidence_score: float
    is_negative: bool  # True if from losing creative (anti-pattern)
    source_creative_id: str


@dataclass
class PremiseExtractionResult:
    """Result of premise extraction."""

    creative_id: str
    test_result: str
    premises_extracted: int
    premises_created: int
    learnings_updated: int
    errors: List[str]


def get_headers():
    """Get Supabase REST API headers for genomai schema."""
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
        "Accept-Profile": "genomai",
        "Content-Profile": "genomai",
    }


# LLM prompt for premise extraction
PREMISE_EXTRACTION_PROMPT = """You are analyzing a creative advertisement to extract PREMISE patterns.

A PREMISE is a narrative vehicle that makes the product story believable and memorable.
It's the "hook" or "angle" that frames the message.

## PREMISE TYPES:
- method: A specific technique or ritual ("lemon seed method", "2-minute morning routine")
- discovery: A revelation or finding ("ancient Tibetan discovery", "accidental lab finding")
- confession: An insider admission ("doctor's confession", "pharma whistleblower")
- secret: Hidden information ("suppressed remedy", "what they don't want you to know")
- ingredient: A specific compound ("single kitchen ingredient", "forgotten herb")
- mechanism: Root cause explanation ("hidden trigger", "real reason behind...")
- breakthrough: New research/science ("Stanford study", "Nobel prize discovery")
- transformation: Change narrative ("one simple change", "before/after secret")

## CREATIVE DATA:
Test Result: {test_result}
Vertical: {vertical}
Geo: {geo}

### Decomposed Variables:
{payload_json}

### Transcript (if available):
{transcript}

### Performance Metrics:
- Spend: ${spend}
- Revenue: ${revenue}
- CPA: ${cpa}
- ROI: {roi}%

## YOUR TASK:
1. Identify the PREMISE pattern(s) used in this creative
2. For WINNING creatives: Extract what makes the premise effective
3. For LOSING creatives: Identify why the premise didn't work (anti-pattern)

## OUTPUT FORMAT:
Return JSON object:
{{
  "premises": [
    {{
      "premise_type": "method|discovery|confession|secret|ingredient|mechanism|breakthrough|transformation",
      "name": "Short memorable name for this premise (5-8 words)",
      "origin_story": "How/where this was discovered (2-3 sentences) or null",
      "mechanism_claim": "What it claims to do (1-2 sentences) or null",
      "confidence_score": 0.0-1.0,
      "is_negative": true/false (true if this is an anti-pattern from losing creative)
    }}
  ],
  "analysis": "Brief explanation of why this premise worked/failed"
}}

If no clear premise pattern found, return: {{"premises": [], "analysis": "No clear premise identified"}}
"""


@activity.defn
async def load_creative_data(creative_id: str) -> CreativeData:
    """
    Load all data for a creative: decomposed, transcript, metrics.

    Returns aggregated CreativeData object.
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ApplicationError("Supabase credentials not configured")

    async with httpx.AsyncClient() as client:
        # Load creative
        response = await client.get(
            f"{SUPABASE_URL}/rest/v1/creatives"
            f"?id=eq.{creative_id}"
            f"&select=id,video_url,tracker_id,test_result,target_vertical,target_geo",
            headers=get_headers(),
        )

        if response.status_code != 200 or not response.json():
            raise ApplicationError(f"Creative not found: {creative_id}")

        creative = response.json()[0]

        # Load decomposed_creatives
        response = await client.get(
            f"{SUPABASE_URL}/rest/v1/decomposed_creatives"
            f"?creative_id=eq.{creative_id}"
            f"&select=payload"
            f"&limit=1",
            headers=get_headers(),
        )

        payload = None
        if response.status_code == 200 and response.json():
            payload = response.json()[0].get("payload")

        # Load transcript
        response = await client.get(
            f"{SUPABASE_URL}/rest/v1/transcripts"
            f"?creative_id=eq.{creative_id}"
            f"&select=transcript_text"
            f"&limit=1",
            headers=get_headers(),
        )

        transcript = None
        if response.status_code == 200 and response.json():
            transcript = response.json()[0].get("transcript_text")

        # Load metrics from daily_metrics_snapshot
        spend = 0.0
        revenue = 0.0
        cpa = None
        roi = None

        if creative.get("tracker_id"):
            response = await client.get(
                f"{SUPABASE_URL}/rest/v1/daily_metrics_snapshot"
                f"?tracker_id=eq.{creative['tracker_id']}"
                f"&select=metrics"
                f"&order=date.desc"
                f"&limit=1",
                headers=get_headers(),
            )

            if response.status_code == 200 and response.json():
                metrics = response.json()[0].get("metrics", {})
                spend = float(metrics.get("spend", 0) or 0)
                revenue = float(metrics.get("revenue", 0) or 0)
                if spend > 0:
                    cpa = spend / max(metrics.get("conversions", 1), 1)
                    roi = ((revenue - spend) / spend) * 100

        activity.logger.info(
            f"Loaded creative {creative_id}: "
            f"result={creative.get('test_result')}, "
            f"has_payload={payload is not None}, "
            f"has_transcript={transcript is not None}"
        )

        return CreativeData(
            creative_id=creative_id,
            video_url=creative.get("video_url"),
            test_result=creative.get("test_result") or "unknown",
            tracker_id=creative.get("tracker_id"),
            vertical=creative.get("target_vertical"),
            geo=creative.get("target_geo"),
            payload=payload,
            transcript_text=transcript,
            spend=spend,
            revenue=revenue,
            cpa=cpa,
            roi=roi,
        )


@activity.defn
async def extract_premises_via_llm(data: CreativeData) -> List[ExtractedPremise]:
    """
    Use LLM to extract premise patterns from creative data.

    Works for both winning and losing creatives.
    """
    import openai

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ApplicationError("OPENAI_API_KEY not configured")

    # Skip if no useful data
    if not data.payload and not data.transcript_text:
        activity.logger.warning(
            f"No payload or transcript for {data.creative_id}, skipping extraction"
        )
        return []

    # Format prompt
    payload_json = (
        json.dumps(data.payload, indent=2, ensure_ascii=False)
        if data.payload
        else "N/A"
    )
    transcript = data.transcript_text[:8000] if data.transcript_text else "N/A"

    prompt = PREMISE_EXTRACTION_PROMPT.format(
        test_result=data.test_result.upper(),
        vertical=data.vertical or "unknown",
        geo=data.geo or "unknown",
        payload_json=payload_json,
        transcript=transcript,
        spend=f"{data.spend:.2f}",
        revenue=f"{data.revenue:.2f}",
        cpa=f"{data.cpa:.2f}" if data.cpa else "N/A",
        roi=f"{data.roi:.1f}" if data.roi else "N/A",
    )

    client = openai.OpenAI(api_key=api_key)

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert creative analyst."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=2000,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        if not content:
            activity.logger.warning("Empty LLM response")
            return []

        result = json.loads(content)
        premises = result.get("premises", [])

        activity.logger.info(
            f"Extracted {len(premises)} premises from {data.creative_id}: "
            f"{result.get('analysis', 'N/A')[:100]}"
        )

        extracted = []
        for p in premises:
            extracted.append(
                ExtractedPremise(
                    premise_type=p.get("premise_type", "method"),
                    name=p.get("name", "Unknown"),
                    origin_story=p.get("origin_story"),
                    mechanism_claim=p.get("mechanism_claim"),
                    confidence_score=float(p.get("confidence_score", 0.5)),
                    is_negative=bool(p.get("is_negative", data.test_result == "loss")),
                    source_creative_id=data.creative_id,
                )
            )

        return extracted

    except json.JSONDecodeError as e:
        activity.logger.error(f"Failed to parse LLM response: {e}")
        return []
    except openai.APIError as e:
        activity.logger.error(f"OpenAI API error: {e}")
        raise ApplicationError(f"LLM extraction failed: {e}")


@activity.defn
async def upsert_premise_and_learning(
    premise: ExtractedPremise,
    test_result: str,
    geo: Optional[str],
    spend: float,
    revenue: float,
) -> dict:
    """
    Create or update premise and its learning record.

    For negative premises (from losers), creates with status='dead'.
    For positive premises, creates with status='emerging'.

    Also updates premise_learnings with win/loss data.
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ApplicationError("Supabase credentials not configured")

    async with httpx.AsyncClient() as client:
        # Check if premise with same name exists
        response = await client.get(
            f"{SUPABASE_URL}/rest/v1/premises?name=eq.{premise.name}&select=id,status",
            headers=get_headers(),
        )

        premise_id = None
        is_new = False

        if response.status_code == 200 and response.json():
            # Premise exists
            existing = response.json()[0]
            premise_id = existing["id"]
            activity.logger.info(f"Found existing premise: {premise_id}")
        else:
            # Create new premise
            status = "dead" if premise.is_negative else "emerging"

            premise_data = {
                "premise_type": premise.premise_type,
                "name": premise.name,
                "origin_story": premise.origin_story,
                "mechanism_claim": premise.mechanism_claim,
                "source": "data_extracted",
                "status": status,
            }

            response = await client.post(
                f"{SUPABASE_URL}/rest/v1/premises",
                headers=get_headers(),
                json=premise_data,
            )

            if response.status_code not in (200, 201):
                # Might be duplicate due to race condition
                activity.logger.warning(
                    f"Failed to create premise: {response.status_code}"
                )
                return {"success": False, "error": "Failed to create premise"}

            premise_id = response.json()[0]["id"]
            is_new = True
            activity.logger.info(f"Created new premise: {premise_id} (status={status})")

        # Update premise_learnings
        was_win = test_result == "win"

        # Check existing learning
        filters = [f"premise_id=eq.{premise_id}"]
        if geo:
            filters.append(f"geo=eq.{geo}")
        else:
            filters.append("geo=is.null")
        filters.append("avatar_id=is.null")

        filter_str = "&".join(filters)

        response = await client.get(
            f"{SUPABASE_URL}/rest/v1/premise_learnings?{filter_str}",
            headers=get_headers(),
        )

        if response.status_code == 200 and response.json():
            # Update existing
            learning = response.json()[0]
            new_sample = (learning.get("sample_size") or 0) + 1
            new_wins = (learning.get("win_count") or 0) + (1 if was_win else 0)
            new_losses = (learning.get("loss_count") or 0) + (0 if was_win else 1)
            new_spend = float(learning.get("total_spend") or 0) + spend
            new_revenue = float(learning.get("total_revenue") or 0) + revenue

            response = await client.patch(
                f"{SUPABASE_URL}/rest/v1/premise_learnings?id=eq.{learning['id']}",
                headers=get_headers(),
                json={
                    "sample_size": new_sample,
                    "win_count": new_wins,
                    "loss_count": new_losses,
                    "total_spend": new_spend,
                    "total_revenue": new_revenue,
                    "updated_at": "now()",
                },
            )
        else:
            # Create new learning
            response = await client.post(
                f"{SUPABASE_URL}/rest/v1/premise_learnings",
                headers=get_headers(),
                json={
                    "premise_id": premise_id,
                    "premise_type": premise.premise_type,
                    "geo": geo,
                    "avatar_id": None,
                    "sample_size": 1,
                    "win_count": 1 if was_win else 0,
                    "loss_count": 0 if was_win else 1,
                    "total_spend": spend,
                    "total_revenue": revenue,
                },
            )

        return {
            "success": True,
            "premise_id": premise_id,
            "is_new": is_new,
            "was_win": was_win,
        }


@activity.defn
async def emit_premise_extraction_event(
    creative_id: str,
    premises_count: int,
    test_result: str,
) -> bool:
    """Emit event to event_log for observability."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return False

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{SUPABASE_URL}/rest/v1/event_log",
            headers=get_headers(),
            json={
                "event_type": "PremiseExtracted",
                "entity_type": "creative",
                "entity_id": creative_id,
                "payload": {
                    "premises_count": premises_count,
                    "test_result": test_result,
                    "source": "premise_extraction_workflow",
                },
            },
        )

        return response.status_code in (200, 201)
