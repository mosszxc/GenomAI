#!/usr/bin/env python3
"""
Test script for HistoricalImportWorkflow.

Usage:
    python -m scripts.test_historical_import <buyer_id> <keitaro_source>

Example:
    python -m scripts.test_historical_import d7024747-c1c4-4844-ab60-513351cc38cd tu
"""

import asyncio
import sys
from dataclasses import asdict

# Add parent directory to path
sys.path.insert(0, ".")

from temporal.client import get_temporal_client
from temporal.models.buyer import HistoricalImportInput
from temporal.workflows.historical_import import HistoricalImportWorkflow


async def main(buyer_id: str, keitaro_source: str):
    """Start HistoricalImportWorkflow."""
    client = await get_temporal_client()

    workflow_id = f"historical-import-{buyer_id}"
    input_data = HistoricalImportInput(
        buyer_id=buyer_id,
        keitaro_source=keitaro_source,
    )

    print("Starting HistoricalImportWorkflow...")
    print(f"  Workflow ID: {workflow_id}")
    print(f"  Buyer ID: {buyer_id}")
    print(f"  Keitaro Source: {keitaro_source}")

    handle = await client.start_workflow(
        HistoricalImportWorkflow.run,
        input_data,
        id=workflow_id,
        task_queue="telegram",
    )

    print(f"\nWorkflow started: {handle.id}")
    print("Waiting for result...")

    result = await handle.result()

    print("\n--- Result ---")
    if hasattr(result, "__dict__"):
        for k, v in asdict(result).items():
            print(f"  {k}: {v}")
    else:
        print(result)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(
            "Usage: python -m scripts.test_historical_import <buyer_id> <keitaro_source>"
        )
        sys.exit(1)

    buyer_id = sys.argv[1]
    keitaro_source = sys.argv[2]

    asyncio.run(main(buyer_id, keitaro_source))
