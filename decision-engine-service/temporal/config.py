"""
Temporal Configuration

Environment variables:
- TEMPORAL_ADDRESS: Temporal server address (default: localhost:7233)
- TEMPORAL_NAMESPACE: Temporal namespace (default: default)
- TEMPORAL_API_KEY: API key for Temporal Cloud (optional)
- TEMPORAL_TLS_ENABLED: Enable TLS (default: false for local, true for cloud)

Supabase (inherited from existing config):
- SUPABASE_URL
- SUPABASE_SERVICE_ROLE_KEY

External APIs:
- OPENAI_API_KEY
- ASSEMBLYAI_API_KEY
- TELEGRAM_BOT_TOKEN
- KEITARO_API_KEY
- KEITARO_BASE_URL
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class TemporalSettings:
    """Temporal connection settings."""

    address: str
    namespace: str
    api_key: Optional[str]
    tls_enabled: bool

    # Task queues
    TASK_QUEUE_CREATIVE_PIPELINE: str = "creative-pipeline"
    TASK_QUEUE_TELEGRAM: str = "telegram"
    TASK_QUEUE_METRICS: str = "metrics"


@dataclass
class SupabaseSettings:
    """Supabase connection settings."""

    url: str
    service_role_key: str
    schema: str = "genomai"


@dataclass
class ExternalAPISettings:
    """External API credentials."""

    openai_api_key: Optional[str]
    assemblyai_api_key: Optional[str]
    telegram_bot_token: Optional[str]
    keitaro_api_key: Optional[str]
    keitaro_base_url: Optional[str]


@dataclass
class Settings:
    """Application settings."""

    temporal: TemporalSettings
    supabase: SupabaseSettings
    external: ExternalAPISettings

    # Feature flags for shadow mode / rollback
    use_temporal_creative_pipeline: bool = False
    use_temporal_telegram: bool = False
    use_temporal_metrics: bool = False


def load_settings() -> Settings:
    """Load settings from environment variables."""

    # Detect if using Temporal Cloud (has tmprl.cloud or temporal.io in address)
    temporal_address = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
    is_cloud = "tmprl.cloud" in temporal_address or ".temporal.io" in temporal_address

    return Settings(
        temporal=TemporalSettings(
            address=temporal_address,
            namespace=os.getenv("TEMPORAL_NAMESPACE", "default"),
            api_key=os.getenv("TEMPORAL_API_KEY"),
            tls_enabled=os.getenv("TEMPORAL_TLS_ENABLED", str(is_cloud)).lower() == "true",
        ),
        supabase=SupabaseSettings(
            url=os.getenv("SUPABASE_URL", ""),
            service_role_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
            schema=os.getenv("SUPABASE_SCHEMA", "genomai"),
        ),
        external=ExternalAPISettings(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            assemblyai_api_key=os.getenv("ASSEMBLYAI_API_KEY"),
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
            keitaro_api_key=os.getenv("KEITARO_API_KEY"),
            keitaro_base_url=os.getenv("KEITARO_BASE_URL"),
        ),
        # Feature flags (default off during migration)
        use_temporal_creative_pipeline=os.getenv("USE_TEMPORAL_CREATIVE_PIPELINE", "false").lower() == "true",
        use_temporal_telegram=os.getenv("USE_TEMPORAL_TELEGRAM", "false").lower() == "true",
        use_temporal_metrics=os.getenv("USE_TEMPORAL_METRICS", "false").lower() == "true",
    )


# Singleton settings instance
settings = load_settings()
