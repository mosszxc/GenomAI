"""
Temporal Client Singleton

Provides a single Temporal client instance for the application.
Handles both Temporal Cloud (with TLS/API key) and local development.
"""

import ssl
from typing import Optional

from temporalio.client import Client, TLSConfig

from temporal.config import settings


_client: Optional[Client] = None


async def get_temporal_client() -> Client:
    """
    Get or create Temporal client singleton.

    Returns:
        Connected Temporal client

    Example:
        client = await get_temporal_client()
        handle = await client.start_workflow(
            MyWorkflow.run,
            input_data,
            id="my-workflow-id",
            task_queue="my-queue"
        )
    """
    global _client

    if _client is not None:
        return _client

    # Build connection options
    connect_kwargs = {
        "target_host": settings.temporal.address,
        "namespace": settings.temporal.namespace,
    }

    # Configure TLS for Temporal Cloud
    if settings.temporal.tls_enabled:
        # For Temporal Cloud with API key authentication
        if settings.temporal.api_key:
            connect_kwargs["api_key"] = settings.temporal.api_key
            connect_kwargs["tls"] = True
        else:
            # For self-hosted with TLS
            connect_kwargs["tls"] = TLSConfig()

    _client = await Client.connect(**connect_kwargs)

    return _client


async def close_temporal_client() -> None:
    """Close the Temporal client connection."""
    global _client

    if _client is not None:
        await _client.close()
        _client = None
