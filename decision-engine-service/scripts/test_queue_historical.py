#!/usr/bin/env python3
"""
Test script for queue_historical_import activity.

Usage:
    python -m scripts.test_queue_historical
"""

import asyncio
import os
from src.core.http_client import get_http_client
from datetime import datetime

# Load env
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")


async def test_insert():
    """Test inserting into historical_import_queue."""

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=representation",
        "Content-Profile": "genomai",
        "Accept-Profile": "genomai",
    }

    base_url = f"{SUPABASE_URL}/rest/v1"

    # Test entry (upsert)
    queue_entry = {
        "buyer_id": "d7024747-c1c4-4844-ab60-513351cc38cd",  # New TU buyer
        "campaign_id": "test-campaign-upsert",
        "video_url": None,
        "keitaro_source": "tu",
        "metrics": None,
        "status": "pending_video",
        "updated_at": datetime.utcnow().isoformat(),
    }

    print("Upserting queue entry:")
    for k, v in queue_entry.items():
        print(f"  {k}: {v}")

    client = get_http_client()
    try:
        # First insert
        response = await client.post(
            f"{base_url}/historical_import_queue?on_conflict=campaign_id",
            headers=headers,
            json=queue_entry,
            timeout=30.0,
        )
        print(f"\nStatus: {response.status_code}")
        print(f"Response: {response.text}")

        if response.status_code >= 400:
            print("\n❌ FIRST INSERT FAILED")
            return

        print("\n✅ FIRST INSERT SUCCESS")
        first_id = response.json()[0]["id"]
        print(f"   ID: {first_id}")

        # Second insert (same campaign_id - should upsert)
        print("\n--- Testing duplicate insert (should upsert) ---")
        queue_entry["updated_at"] = datetime.utcnow().isoformat()
        response2 = await client.post(
            f"{base_url}/historical_import_queue?on_conflict=campaign_id",
            headers=headers,
            json=queue_entry,
            timeout=30.0,
        )
        print(f"Status: {response2.status_code}")

        if response2.status_code >= 400:
            print("❌ UPSERT FAILED")
        else:
            second_id = response2.json()[0]["id"]
            print(f"✅ UPSERT SUCCESS - ID: {second_id}")
            if first_id == second_id:
                print("   ✅ Same ID - upsert worked correctly!")
            else:
                print("   ⚠️ Different ID - created new record")

        # Clean up
        delete_resp = await client.delete(
            f"{base_url}/historical_import_queue?campaign_id=eq.test-campaign-upsert",
            headers=headers,
        )
        print(f"\nCleanup: {delete_resp.status_code}")

    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_insert())
