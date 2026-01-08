"""
GenomAI Temporal Workflow Orchestration

This module contains Temporal workflows and activities for the GenomAI
creative decision system, replacing n8n workflow orchestration.

Structure:
- workflows/: Temporal workflow definitions
- activities/: Activity implementations (external calls, DB operations)
- models/: Pydantic models for workflow inputs/outputs
- config.py: Environment configuration
- client.py: Temporal client singleton
- worker.py: Worker entrypoint
"""

from temporal.config import settings

__all__ = ["settings"]
