"""
Module Selector Service

Prioritized selection of modules for hypothesis generation.
Implements 90/10 exploitation/exploration split.

Part of Modular Creative System (Phase 3).
"""

import os
from typing import Optional, List, Dict, Any, Tuple
from src.core.http_client import get_http_client

# Schema name for all operations
SCHEMA = "genomai"

# Selection constants
EXPLOITATION_RATIO = 0.9  # 90% top performers
EXPLORATION_RATIO = 0.1  # 10% under-explored
EXPLORATION_SAMPLE_THRESHOLD = 5  # sample_size < 5 = exploration

# Minimum modules required for modular generation
MIN_HOOKS_REQUIRED = 3
MIN_PROMISES_REQUIRED = 3
MIN_PROOFS_REQUIRED = 2
MIN_EXPLORED_MODULES = 2  # At least 2 modules with sample_size >= 5


def _get_credentials() -> Tuple[str, str]:
    """Get Supabase credentials from environment."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        raise RuntimeError("Missing Supabase credentials")

    rest_url = f"{supabase_url}/rest/v1"
    return rest_url, supabase_key


def _get_headers(supabase_key: str) -> dict:
    """Get headers for Supabase REST API with genomai schema."""
    return {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Accept-Profile": SCHEMA,
        "Content-Type": "application/json",
    }


async def check_modular_generation_ready(
    vertical: Optional[str] = None,
    geo: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Check if enough modules exist for modular generation.

    Conditions for modular generation:
    - At least MIN_HOOKS_REQUIRED active hooks
    - At least MIN_PROMISES_REQUIRED active promises
    - At least MIN_PROOFS_REQUIRED active proofs
    - At least MIN_EXPLORED_MODULES modules with sample_size >= 5

    Args:
        vertical: Optional filter by vertical
        geo: Optional filter by GEO

    Returns:
        Dict with:
            - ready: bool - whether modular generation can be used
            - hooks_count: int
            - promises_count: int
            - proofs_count: int
            - explored_count: int - modules with sample_size >= 5
            - reason: str - reason if not ready
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    # Build filter
    filters = ["status=eq.active"]
    if vertical:
        filters.append(f"vertical=eq.{vertical}")
    if geo:
        filters.append(f"geo=eq.{geo}")

    filter_str = "&".join(filters)

    client = get_http_client()
    # Count by module type
    counts = {}
    for module_type in ["hook", "promise", "proof"]:
        response = await client.get(
            f"{rest_url}/module_bank?module_type=eq.{module_type}&{filter_str}&select=id",
            headers=headers,
        )
        response.raise_for_status()
        counts[module_type] = len(response.json())

    # Count explored modules (sample_size >= 5)
    response = await client.get(
        f"{rest_url}/module_bank"
        f"?sample_size=gte.{EXPLORATION_SAMPLE_THRESHOLD}&{filter_str}"
        f"&select=id",
        headers=headers,
    )
    response.raise_for_status()
    explored_count = len(response.json())

    # Check conditions
    hooks_ok = counts["hook"] >= MIN_HOOKS_REQUIRED
    promises_ok = counts["promise"] >= MIN_PROMISES_REQUIRED
    proofs_ok = counts["proof"] >= MIN_PROOFS_REQUIRED
    explored_ok = explored_count >= MIN_EXPLORED_MODULES

    ready = hooks_ok and promises_ok and proofs_ok and explored_ok

    reason = None
    if not ready:
        missing = []
        if not hooks_ok:
            missing.append(f"hooks: {counts['hook']}/{MIN_HOOKS_REQUIRED}")
        if not promises_ok:
            missing.append(f"promises: {counts['promise']}/{MIN_PROMISES_REQUIRED}")
        if not proofs_ok:
            missing.append(f"proofs: {counts['proof']}/{MIN_PROOFS_REQUIRED}")
        if not explored_ok:
            missing.append(f"explored: {explored_count}/{MIN_EXPLORED_MODULES}")
        reason = f"Insufficient modules: {', '.join(missing)}"

    return {
        "ready": ready,
        "hooks_count": counts["hook"],
        "promises_count": counts["promise"],
        "proofs_count": counts["proof"],
        "explored_count": explored_count,
        "reason": reason,
    }


async def select_modules(
    module_type: str,
    count: int,
    vertical: Optional[str] = None,
    geo: Optional[str] = None,
    exclude_ids: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Select modules with 90/10 exploitation/exploration split.

    Algorithm:
    - 90% from top performers (highest win_rate, status=active)
    - 10% from under-explored (sample_size < 5)

    Args:
        module_type: hook, promise, or proof
        count: Number of modules to select
        vertical: Optional filter by vertical
        geo: Optional filter by GEO
        exclude_ids: Module IDs to exclude

    Returns:
        List of selected module dicts with id, content, win_rate, sample_size
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    # Calculate split
    exploitation_count = max(1, int(count * EXPLOITATION_RATIO))
    exploration_count = count - exploitation_count

    # Build base filter
    filters = [f"module_type=eq.{module_type}"]
    if vertical:
        filters.append(f"vertical=eq.{vertical}")
    if geo:
        filters.append(f"geo=eq.{geo}")

    exclude_filter = ""
    if exclude_ids:
        exclude_filter = f"&id=not.in.({','.join(exclude_ids)})"

    base_filter = "&".join(filters)

    selected = []

    client = get_http_client()
    # 1. Exploitation: top performers by win_rate
    response = await client.get(
        f"{rest_url}/module_bank"
        f"?{base_filter}&status=eq.active{exclude_filter}"
        f"&select=id,content,text_content,win_rate,sample_size,module_key"
        f"&order=win_rate.desc"
        f"&limit={exploitation_count}",
        headers=headers,
    )
    response.raise_for_status()
    exploitation_modules = response.json()
    selected.extend(exploitation_modules)

    # Track already selected IDs
    selected_ids = [m["id"] for m in selected]
    if exclude_ids:
        selected_ids.extend(exclude_ids)

    # 2. Exploration: under-explored modules
    if exploration_count > 0 and selected_ids:
        exclude_str = ",".join(selected_ids)
        response = await client.get(
            f"{rest_url}/module_bank"
            f"?{base_filter}"
            f"&sample_size=lt.{EXPLORATION_SAMPLE_THRESHOLD}"
            f"&id=not.in.({exclude_str})"
            f"&select=id,content,text_content,win_rate,sample_size,module_key"
            f"&order=created_at.desc"
            f"&limit={exploration_count}",
            headers=headers,
        )
        response.raise_for_status()
        exploration_modules = response.json()
        selected.extend(exploration_modules)

    return selected


async def get_compatibility_score(
    module_a_id: str,
    module_b_id: str,
) -> float:
    """
    Get compatibility score between two modules.

    Returns 0.5 (neutral) if no data exists.

    Args:
        module_a_id: First module UUID
        module_b_id: Second module UUID

    Returns:
        Compatibility score (0.0 to 1.0)
    """
    rest_url, supabase_key = _get_credentials()
    headers = _get_headers(supabase_key)

    # Ensure consistent ordering (module_a_id < module_b_id as per constraint)
    if module_a_id > module_b_id:
        module_a_id, module_b_id = module_b_id, module_a_id

    client = get_http_client()
    response = await client.get(
        f"{rest_url}/module_compatibility"
        f"?module_a_id=eq.{module_a_id}"
        f"&module_b_id=eq.{module_b_id}"
        f"&select=compatibility_score",
        headers=headers,
    )
    response.raise_for_status()
    data = response.json()

    if data:
        return float(data[0].get("compatibility_score", 0.5))

    return 0.5  # Default neutral score


async def select_compatible_modules(
    module_type: str,
    count: int,
    reference_module_ids: List[str],
    vertical: Optional[str] = None,
    geo: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Select modules compatible with reference modules.

    Combines win_rate with compatibility scores for ranking.

    Args:
        module_type: hook, promise, or proof
        count: Number of modules to select
        reference_module_ids: Module IDs to check compatibility against
        vertical: Optional filter by vertical
        geo: Optional filter by GEO

    Returns:
        List of selected modules ranked by combined score
    """
    # Get candidate modules
    candidates = await select_modules(
        module_type=module_type,
        count=count * 3,  # Get more candidates for filtering
        vertical=vertical,
        geo=geo,
        exclude_ids=reference_module_ids,
    )

    if not candidates or not reference_module_ids:
        return candidates[:count]

    # Calculate combined scores with compatibility
    scored_candidates = []
    for candidate in candidates:
        win_rate = float(candidate.get("win_rate", 0) or 0)

        # Average compatibility with reference modules
        compat_scores = []
        for ref_id in reference_module_ids:
            score = await get_compatibility_score(candidate["id"], ref_id)
            compat_scores.append(score)

        avg_compat = sum(compat_scores) / len(compat_scores) if compat_scores else 0.5

        # Combined score: 70% win_rate + 30% compatibility
        combined_score = 0.7 * win_rate + 0.3 * avg_compat

        scored_candidates.append(
            {
                **candidate,
                "combined_score": combined_score,
                "avg_compatibility": avg_compat,
            }
        )

    # Sort by combined score
    scored_candidates.sort(key=lambda x: x["combined_score"], reverse=True)

    return scored_candidates[:count]


async def select_module_combination(
    vertical: Optional[str] = None,
    geo: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Select a complete module combination (hook + promise + proof).

    Algorithm:
    1. Select top hook with 90/10 split
    2. Select compatible promise
    3. Select compatible proof

    Args:
        vertical: Optional filter by vertical
        geo: Optional filter by GEO

    Returns:
        Dict with:
            - hook: module dict
            - promise: module dict
            - proof: module dict
            - combined_score: float
        Or None if no valid combination found
    """
    # 1. Select hook
    hooks = await select_modules(
        module_type="hook",
        count=1,
        vertical=vertical,
        geo=geo,
    )

    if not hooks:
        return None

    hook = hooks[0]

    # 2. Select promise compatible with hook
    promises = await select_compatible_modules(
        module_type="promise",
        count=1,
        reference_module_ids=[hook["id"]],
        vertical=vertical,
        geo=geo,
    )

    if not promises:
        return None

    promise = promises[0]

    # 3. Select proof compatible with both hook and promise
    proofs = await select_compatible_modules(
        module_type="proof",
        count=1,
        reference_module_ids=[hook["id"], promise["id"]],
        vertical=vertical,
        geo=geo,
    )

    if not proofs:
        return None

    proof = proofs[0]

    # Calculate combined score
    hook_score = float(hook.get("win_rate", 0) or 0)
    promise_score = float(promise.get("combined_score", promise.get("win_rate", 0)) or 0)
    proof_score = float(proof.get("combined_score", proof.get("win_rate", 0)) or 0)

    combined_score = (hook_score + promise_score + proof_score) / 3

    return {
        "hook": hook,
        "promise": promise,
        "proof": proof,
        "combined_score": combined_score,
    }


async def select_top_combinations(
    count: int = 3,
    vertical: Optional[str] = None,
    geo: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Select top N module combinations for hypothesis generation.

    Uses greedy algorithm to select diverse, high-performing combinations.

    Args:
        count: Number of combinations to generate
        vertical: Optional filter by vertical
        geo: Optional filter by GEO

    Returns:
        List of module combinations
    """
    combinations: List[Dict[str, Any]] = []
    used_hooks: set[str] = set()
    used_promises: set[str] = set()
    used_proofs: set[str] = set()

    for _ in range(count):
        # Get more hooks to find unused ones
        hooks = await select_modules(
            module_type="hook",
            count=count * 2,
            vertical=vertical,
            geo=geo,
        )

        # Find first unused hook
        hook = None
        for h in hooks:
            if h["id"] not in used_hooks:
                hook = h
                break

        if not hook:
            break

        used_hooks.add(hook["id"])

        # Get compatible promises
        promises = await select_compatible_modules(
            module_type="promise",
            count=count * 2,
            reference_module_ids=[hook["id"]],
            vertical=vertical,
            geo=geo,
        )

        # Find first unused promise
        promise = None
        for p in promises:
            if p["id"] not in used_promises:
                promise = p
                break

        if not promise:
            continue

        used_promises.add(promise["id"])

        # Get compatible proofs
        proofs = await select_compatible_modules(
            module_type="proof",
            count=count * 2,
            reference_module_ids=[hook["id"], promise["id"]],
            vertical=vertical,
            geo=geo,
        )

        # Find first unused proof
        proof = None
        for p in proofs:
            if p["id"] not in used_proofs:
                proof = p
                break

        if not proof:
            continue

        used_proofs.add(proof["id"])

        # Calculate combined score
        hook_score = float(hook.get("win_rate", 0) or 0)
        promise_score = float(promise.get("combined_score", promise.get("win_rate", 0)) or 0)
        proof_score = float(proof.get("combined_score", proof.get("win_rate", 0)) or 0)

        combinations.append(
            {
                "hook": hook,
                "promise": promise,
                "proof": proof,
                "combined_score": (hook_score + promise_score + proof_score) / 3,
            }
        )

    # Sort by combined score
    combinations.sort(key=lambda x: float(x["combined_score"]), reverse=True)

    return combinations
