#!/usr/bin/env python3
"""Terminate a stuck workflow by ID.

Usage:
    python scripts/terminate_workflow.py <workflow_id>

Example:
    python scripts/terminate_workflow.py onboarding-291678304
"""

import asyncio
import sys
import os

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from temporal.client import get_temporal_client


async def terminate_workflow(workflow_id: str) -> None:
    """Terminate a workflow by ID."""
    client = await get_temporal_client()
    handle = client.get_workflow_handle(workflow_id)

    try:
        await handle.terminate(reason="Manual termination via script")
        print(f"✅ Workflow {workflow_id} terminated successfully")
    except Exception as e:
        print(f"❌ Failed to terminate workflow: {e}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/terminate_workflow.py <workflow_id>")
        sys.exit(1)

    workflow_id = sys.argv[1]
    print(f"Terminating workflow: {workflow_id}")
    asyncio.run(terminate_workflow(workflow_id))
