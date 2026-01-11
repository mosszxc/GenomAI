"""
Premise Selection Activity

Temporal activity for selecting premises for hypothesis generation.
Wraps premise_selector.py for use in workflows.

Issue: #402
"""

from typing import Optional
from dataclasses import dataclass, asdict
from temporalio import activity

from src.services.premise_selector import (
    select_premise_for_hypothesis,
    PremiseSelection,
)


@dataclass
class PremiseSelectionResult:
    """Result of premise selection activity."""

    premise_id: Optional[str]
    premise_type: str
    name: str
    origin_story: Optional[str]
    mechanism_claim: Optional[str]
    is_new: bool
    selection_reason: str


@activity.defn
async def select_premise(
    idea_id: str,
    avatar_id: Optional[str] = None,
    geo: Optional[str] = None,
    vertical: Optional[str] = None,
) -> dict:
    """
    Select a premise for hypothesis generation.

    Uses Thompson Sampling for explore/exploit balance:
    - 75% exploitation: Use best performing premise
    - 25% exploration:
      - 70% of exploration: Use undersampled premise
      - 30% of exploration: Signal for LLM generation (is_new=True)

    Args:
        idea_id: The idea for which hypothesis is being generated
        avatar_id: Optional avatar context for personalization
        geo: Optional geo context for targeting
        vertical: Optional vertical filter

    Returns:
        dict with premise details or is_new=True signal
    """
    activity.logger.info(
        f"Selecting premise for idea={idea_id}, geo={geo}, vertical={vertical}"
    )

    selection: PremiseSelection = await select_premise_for_hypothesis(
        idea_id=idea_id,
        avatar_id=avatar_id,
        geo=geo,
        vertical=vertical,
    )

    result = PremiseSelectionResult(
        premise_id=selection.premise_id,
        premise_type=selection.premise_type,
        name=selection.name,
        origin_story=selection.origin_story,
        mechanism_claim=selection.mechanism_claim,
        is_new=selection.is_new,
        selection_reason=selection.selection_reason,
    )

    activity.logger.info(
        f"Selected premise: id={result.premise_id}, "
        f"type={result.premise_type}, reason={result.selection_reason}"
    )

    return asdict(result)
