"""
Temporal Client Singleton

Provides a single Temporal client instance for the application.
Handles both Temporal Cloud (with TLS/API key) and local development.
"""

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

    # Build connection options (endpoint must be positional argument for Temporal Cloud)
    connect_kwargs = {
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

    # Connect with endpoint as first positional argument (required for Temporal Cloud)
    _client = await Client.connect(settings.temporal.address, **connect_kwargs)

    return _client


async def close_temporal_client() -> None:
    """Close the Temporal client connection.

    Note: Temporal SDK Client doesn't have a close() method.
    This function just clears the singleton reference.
    """
    global _client
    _client = None
