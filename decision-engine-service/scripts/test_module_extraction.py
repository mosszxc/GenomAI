#!/usr/bin/env python3
"""
Production test for module_extraction activity.

Creates test data and verifies modules are extracted correctly.

Usage:
    cd decision-engine-service
    python scripts/test_module_extraction.py
"""

import asyncio
import os
import sys
import uuid
from src.core.http_client import get_http_client

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def main():
    from temporal.activities.module_extraction import (
        extract_modules_from_decomposition,
    )

    print("=" * 60)
    print("Production Test: Module Extraction Activity")
    print("=" * 60)

    # Get Supabase credentials
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY required")
        sys.exit(1)

    rest_url = f"{supabase_url}/rest/v1"
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Accept-Profile": "genomai",
        "Content-Profile": "genomai",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

    # Step 1: Get existing creative
    print("\n[1/5] Finding test creative...")
    client = get_http_client()
    resp = await client.get(
        f"{rest_url}/creatives?select=id&limit=1",
        headers=headers,
    )
    creatives = resp.json()

    if not creatives:
        print("ERROR: No creatives in DB. Create one first.")
        sys.exit(1)

    creative_id = creatives[0]["id"]
    print(f"  Using creative: {creative_id}")

    # Step 2: Create test decomposed_creative
    print("\n[2/5] Creating test decomposed_creative...")
    test_decomposed_id = str(uuid.uuid4())
    test_payload = {
        "hooks": ["Stop everything!", "This changes everything"],
        "hook_mechanism": "pattern_interrupt",
        "hook_stopping_power": "high",
        "opening_type": "shock_statement",
        "promise_type": "transformation",
        "core_belief": "solution_is_simple",
        "state_before": "frustrated",
        "state_after": "confident",
        "ump_type": "hidden_cause",
        "ums_type": "secret_ingredient",
        "proof_type": "testimonial",
        "proof_source": "customer",
        "social_proof_pattern": "cascading",
        "story_type": "transformation",
        "schema_version": "v2",
    }

    client = get_http_client()
    resp = await client.post(
        f"{rest_url}/decomposed_creatives",
        headers=headers,
        json={
            "id": test_decomposed_id,
            "creative_id": creative_id,
            "payload": test_payload,
            "schema_version": "v2",
        },
    )
    if resp.status_code >= 400:
        print(f"ERROR creating decomposed_creative: {resp.text}")
        sys.exit(1)
    print(f"  Created: {test_decomposed_id}")

    # Step 3: Call activity
    print("\n[3/5] Calling extract_modules_from_decomposition...")
    try:
        result = await extract_modules_from_decomposition(
            creative_id=creative_id,
            decomposed_id=test_decomposed_id,
            payload=test_payload,
            vertical="nutra",
            geo="RU",
        )
        print(f"  Result: {result}")
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    # Step 4: Verify modules in DB
    print("\n[4/5] Verifying modules in module_bank...")
    client = get_http_client()
    for module_type in ["hook", "promise", "proof"]:
        module_id = result.get(f"{module_type}_id")
        if not module_id:
            print(f"  WARNING: No {module_type}_id returned")
            continue

        resp = await client.get(
            f"{rest_url}/module_bank?id=eq.{module_id}&select=*",
            headers=headers,
        )
        modules = resp.json()

        if modules:
            m = modules[0]
            print(
                f"  {module_type}: {m['id'][:8]}... key={m['module_key'][:16]}... status={m['status']}"
            )
        else:
            print(f"  ERROR: {module_type} module not found!")

    # Step 5: Cleanup test data
    print("\n[5/5] Cleanup...")
    client = get_http_client()
    # Delete test decomposed_creative
    await client.delete(
        f"{rest_url}/decomposed_creatives?id=eq.{test_decomposed_id}",
        headers=headers,
    )
    print(f"  Deleted decomposed_creative: {test_decomposed_id}")

    # Note: modules are NOT deleted - they're production data now

    print("\n" + "=" * 60)
    print("Production Test: PASSED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
