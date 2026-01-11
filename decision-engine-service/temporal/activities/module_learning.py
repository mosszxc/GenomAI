"""
Module Learning Activities

Activities for updating module statistics based on creative test outcomes:
- Update module bank stats (win_count, sample_size, spend, revenue)
- Update module compatibility scores

Part of the Modular Creative System.
Note: win_rate, avg_roi, compatibility_score are GENERATED columns - DO NOT update directly.
"""

from datetime import datetime
from typing import Optional
from dataclasses import dataclass

from temporalio import activity

from temporal.config import settings


SCHEMA = "genomai"


@dataclass
class ModuleOutcome:
    """Outcome data for a single module"""

    module_id: str
    is_win: bool
    spend: float
    revenue: float


@dataclass
class UpdateModuleStatsInput:
    """Input for update_module_stats activity"""

    module_id: str
    is_win: bool
    spend: float = 0.0
    revenue: float = 0.0


@dataclass
class UpdateModuleStatsOutput:
    """Output from update_module_stats activity"""

    success: bool
    module_id: str
    new_sample_size: Optional[int] = None
    new_win_count: Optional[int] = None
    error: Optional[str] = None


@activity.defn
async def update_module_stats(input: UpdateModuleStatsInput) -> UpdateModuleStatsOutput:
    """
    Update statistics for a single module based on creative outcome.

    Increments:
    - sample_size: always +1
    - win_count: +1 if is_win
    - loss_count: +1 if not is_win
    - total_spend: += spend
    - total_revenue: += revenue

    Note: win_rate and avg_roi are generated columns, updated automatically.

    Args:
        input: module_id and outcome data

    Returns:
        UpdateModuleStatsOutput with new stats
    """
    import httpx

    activity.logger.info(
        f"Updating module stats: {input.module_id}, win={input.is_win}"
    )

    headers = {
        "apikey": settings.supabase.service_role_key,
        "Authorization": f"Bearer {settings.supabase.service_role_key}",
        "Accept-Profile": SCHEMA,
        "Content-Profile": SCHEMA,
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

    # First get current stats
    get_url = (
        f"{settings.supabase.url}/rest/v1/module_bank"
        f"?id=eq.{input.module_id}&select=sample_size,win_count,loss_count,total_spend,total_revenue"
    )

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(get_url, headers=headers)
            response.raise_for_status()
            data = response.json()

            if not data:
                activity.logger.warning(f"Module not found: {input.module_id}")
                return UpdateModuleStatsOutput(
                    success=False,
                    module_id=input.module_id,
                    error=f"Module not found: {input.module_id}",
                )

            current = data[0]
            sample_size = (current.get("sample_size") or 0) + 1
            win_count = (current.get("win_count") or 0) + (1 if input.is_win else 0)
            loss_count = (current.get("loss_count") or 0) + (0 if input.is_win else 1)
            total_spend = float(current.get("total_spend") or 0) + input.spend
            total_revenue = float(current.get("total_revenue") or 0) + input.revenue

            # Update stats
            update_url = (
                f"{settings.supabase.url}/rest/v1/module_bank?id=eq.{input.module_id}"
            )
            update_payload = {
                "sample_size": sample_size,
                "win_count": win_count,
                "loss_count": loss_count,
                "total_spend": total_spend,
                "total_revenue": total_revenue,
                "updated_at": datetime.utcnow().isoformat(),
            }

            response = await client.patch(
                update_url, headers=headers, json=update_payload
            )
            response.raise_for_status()

            activity.logger.info(
                f"Module stats updated: {input.module_id}, "
                f"sample_size={sample_size}, win_count={win_count}"
            )

            return UpdateModuleStatsOutput(
                success=True,
                module_id=input.module_id,
                new_sample_size=sample_size,
                new_win_count=win_count,
            )

    except httpx.HTTPStatusError as e:
        activity.logger.error(f"HTTP error updating module: {e.response.status_code}")
        return UpdateModuleStatsOutput(
            success=False,
            module_id=input.module_id,
            error=f"HTTP error: {e.response.status_code}",
        )
    except Exception as e:
        activity.logger.error(f"Error updating module stats: {str(e)}")
        return UpdateModuleStatsOutput(
            success=False,
            module_id=input.module_id,
            error=str(e),
        )


@dataclass
class UpdateCompatibilityInput:
    """Input for update_compatibility_stats activity"""

    module_a_id: str
    module_b_id: str
    is_win: bool


@dataclass
class UpdateCompatibilityOutput:
    """Output from update_compatibility_stats activity"""

    success: bool
    module_a_id: str
    module_b_id: str
    new_sample_size: Optional[int] = None
    new_win_count: Optional[int] = None
    error: Optional[str] = None


@activity.defn
async def update_compatibility_stats(
    input: UpdateCompatibilityInput,
) -> UpdateCompatibilityOutput:
    """
    Update compatibility statistics for a module pair.

    Creates record if not exists, then increments:
    - sample_size: always +1
    - win_count: +1 if is_win

    Note: compatibility_score is a generated column, updated automatically.

    Args:
        input: module pair IDs and outcome

    Returns:
        UpdateCompatibilityOutput with new stats
    """
    import httpx

    # Ensure consistent ordering (smaller UUID first)
    module_a_id, module_b_id = sorted([input.module_a_id, input.module_b_id])

    activity.logger.info(
        f"Updating compatibility: {module_a_id} <-> {module_b_id}, win={input.is_win}"
    )

    headers = {
        "apikey": settings.supabase.service_role_key,
        "Authorization": f"Bearer {settings.supabase.service_role_key}",
        "Accept-Profile": SCHEMA,
        "Content-Profile": SCHEMA,
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

    # Check if pair exists
    get_url = (
        f"{settings.supabase.url}/rest/v1/module_compatibility"
        f"?module_a_id=eq.{module_a_id}&module_b_id=eq.{module_b_id}"
        f"&select=id,sample_size,win_count"
    )

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(get_url, headers=headers)
            response.raise_for_status()
            data = response.json()

            if data:
                # Update existing
                current = data[0]
                sample_size = (current.get("sample_size") or 0) + 1
                win_count = (current.get("win_count") or 0) + (1 if input.is_win else 0)
                record_id = current["id"]

                update_url = (
                    f"{settings.supabase.url}/rest/v1/module_compatibility"
                    f"?id=eq.{record_id}"
                )
                update_payload = {
                    "sample_size": sample_size,
                    "win_count": win_count,
                    "updated_at": datetime.utcnow().isoformat(),
                }

                response = await client.patch(
                    update_url, headers=headers, json=update_payload
                )
                response.raise_for_status()
            else:
                # Create new
                sample_size = 1
                win_count = 1 if input.is_win else 0

                create_url = f"{settings.supabase.url}/rest/v1/module_compatibility"
                create_payload = {
                    "module_a_id": module_a_id,
                    "module_b_id": module_b_id,
                    "sample_size": sample_size,
                    "win_count": win_count,
                }

                response = await client.post(
                    create_url, headers=headers, json=create_payload
                )
                response.raise_for_status()

            activity.logger.info(
                f"Compatibility updated: {module_a_id} <-> {module_b_id}, "
                f"sample_size={sample_size}, win_count={win_count}"
            )

            return UpdateCompatibilityOutput(
                success=True,
                module_a_id=module_a_id,
                module_b_id=module_b_id,
                new_sample_size=sample_size,
                new_win_count=win_count,
            )

    except httpx.HTTPStatusError as e:
        activity.logger.error(
            f"HTTP error updating compatibility: {e.response.status_code}"
        )
        return UpdateCompatibilityOutput(
            success=False,
            module_a_id=module_a_id,
            module_b_id=module_b_id,
            error=f"HTTP error: {e.response.status_code}",
        )
    except Exception as e:
        activity.logger.error(f"Error updating compatibility stats: {str(e)}")
        return UpdateCompatibilityOutput(
            success=False,
            module_a_id=module_a_id,
            module_b_id=module_b_id,
            error=str(e),
        )


@dataclass
class BatchModuleOutcome:
    """Single module outcome in a batch"""

    module_id: str
    is_win: bool
    spend: float = 0.0
    revenue: float = 0.0


@dataclass
class ProcessModuleLearningInput:
    """Input for process_module_learning activity"""

    creative_id: str
    module_ids: list[str]
    is_win: bool
    spend: float = 0.0
    revenue: float = 0.0


@dataclass
class ProcessModuleLearningOutput:
    """Output from process_module_learning activity"""

    success: bool
    creative_id: str
    modules_updated: int
    compatibilities_updated: int
    errors: list[str]


@activity.defn
async def process_module_learning(
    input: ProcessModuleLearningInput,
) -> ProcessModuleLearningOutput:
    """
    Process learning for all modules used in a creative.

    Updates:
    1. Stats for each module in module_bank
    2. Compatibility scores for all module pairs

    Args:
        input: creative_id, list of module_ids, and outcome data

    Returns:
        ProcessModuleLearningOutput with counts
    """
    activity.logger.info(
        f"Processing module learning for creative {input.creative_id}, "
        f"{len(input.module_ids)} modules, win={input.is_win}"
    )

    errors: list[str] = []
    modules_updated = 0
    compatibilities_updated = 0

    # Split spend/revenue evenly across modules
    module_count = len(input.module_ids)
    if module_count == 0:
        return ProcessModuleLearningOutput(
            success=True,
            creative_id=input.creative_id,
            modules_updated=0,
            compatibilities_updated=0,
            errors=[],
        )

    spend_per_module = input.spend / module_count
    revenue_per_module = input.revenue / module_count

    # Update each module
    for module_id in input.module_ids:
        result = await update_module_stats(
            UpdateModuleStatsInput(
                module_id=module_id,
                is_win=input.is_win,
                spend=spend_per_module,
                revenue=revenue_per_module,
            )
        )
        if result.success:
            modules_updated += 1
        elif result.error:
            errors.append(f"Module {module_id}: {result.error}")

    # Update compatibility for all pairs
    for i, module_a in enumerate(input.module_ids):
        for module_b in input.module_ids[i + 1 :]:
            result = await update_compatibility_stats(
                UpdateCompatibilityInput(
                    module_a_id=module_a,
                    module_b_id=module_b,
                    is_win=input.is_win,
                )
            )
            if result.success:
                compatibilities_updated += 1
            elif result.error:
                errors.append(f"Compatibility {module_a}<->{module_b}: {result.error}")

    success = len(errors) == 0
    activity.logger.info(
        f"Module learning complete: {modules_updated} modules, "
        f"{compatibilities_updated} compatibilities, {len(errors)} errors"
    )

    return ProcessModuleLearningOutput(
        success=success,
        creative_id=input.creative_id,
        modules_updated=modules_updated,
        compatibilities_updated=compatibilities_updated,
        errors=errors,
    )
