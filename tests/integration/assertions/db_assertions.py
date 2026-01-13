"""
Database assertion helpers for integration tests.

These functions verify database state after workflow execution.
"""

import httpx
from typing import Optional, Any
import asyncio


class DbAssertions:
    """Database assertion helper for Supabase genomai schema."""

    def __init__(self, base_url: str, headers: dict):
        self.base_url = base_url
        self.headers = headers
        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        await self.client.aclose()

    async def _query(self, table: str, filters: str = "") -> list[dict]:
        """Execute a query against Supabase."""
        url = f"{self.base_url}/rest/v1/{table}?{filters}"
        response = await self.client.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    async def _query_single(self, table: str, filters: str) -> Optional[dict]:
        """Query and return single row or None."""
        results = await self._query(table, filters)
        return results[0] if results else None

    # ==================== Creatives ====================

    async def creative_exists(self, tracker_id: str) -> bool:
        """Check if creative exists by tracker_id."""
        result = await self._query_single(
            "creatives", f"tracker_id=eq.{tracker_id}&select=id"
        )
        return result is not None

    async def get_creative(self, tracker_id: str) -> Optional[dict]:
        """Get creative by tracker_id."""
        return await self._query_single(
            "creatives", f"tracker_id=eq.{tracker_id}&select=*"
        )

    async def creative_has_status(self, tracker_id: str, status: str) -> bool:
        """Check if creative has specific status."""
        creative = await self.get_creative(tracker_id)
        return creative is not None and creative.get("status") == status

    # ==================== Transcripts ====================

    async def transcript_exists(self, creative_id: str) -> bool:
        """Check if transcript exists for creative."""
        result = await self._query_single(
            "transcripts", f"creative_id=eq.{creative_id}&select=id"
        )
        return result is not None

    async def get_transcript(self, creative_id: str) -> Optional[dict]:
        """Get transcript by creative_id."""
        return await self._query_single(
            "transcripts", f"creative_id=eq.{creative_id}&select=*"
        )

    # ==================== Decomposed Creatives ====================

    async def decomposed_exists(self, creative_id: str) -> bool:
        """Check if decomposed creative exists."""
        result = await self._query_single(
            "decomposed_creatives", f"creative_id=eq.{creative_id}&select=id"
        )
        return result is not None

    async def get_decomposed(self, creative_id: str) -> Optional[dict]:
        """Get decomposed creative."""
        return await self._query_single(
            "decomposed_creatives", f"creative_id=eq.{creative_id}&select=*"
        )

    # ==================== Ideas ====================

    async def idea_exists(self, idea_id: str) -> bool:
        """Check if idea exists."""
        result = await self._query_single("ideas", f"id=eq.{idea_id}&select=id")
        return result is not None

    async def get_idea_by_hash(self, canonical_hash: str) -> Optional[dict]:
        """Get idea by canonical hash."""
        return await self._query_single(
            "ideas", f"canonical_hash=eq.{canonical_hash}&select=*"
        )

    async def idea_has_death_state(
        self, idea_id: str, death_state: Optional[str]
    ) -> bool:
        """Check if idea has specific death_state."""
        result = await self._query_single(
            "ideas", f"id=eq.{idea_id}&select=death_state"
        )
        if result is None:
            return False
        return result.get("death_state") == death_state

    # ==================== Decisions ====================

    async def decision_exists(self, idea_id: str) -> bool:
        """Check if decision exists for idea."""
        result = await self._query_single(
            "decisions", f"idea_id=eq.{idea_id}&select=id"
        )
        return result is not None

    async def get_decision(self, idea_id: str) -> Optional[dict]:
        """Get latest decision for idea."""
        results = await self._query(
            "decisions", f"idea_id=eq.{idea_id}&select=*&order=created_at.desc&limit=1"
        )
        return results[0] if results else None

    async def decision_is(self, idea_id: str, expected: str) -> bool:
        """Check if decision matches expected value."""
        decision = await self.get_decision(idea_id)
        return decision is not None and decision.get("decision") == expected

    # ==================== Hypotheses ====================

    async def hypothesis_exists(self, idea_id: str) -> bool:
        """Check if hypothesis exists for idea."""
        result = await self._query_single(
            "hypotheses", f"idea_id=eq.{idea_id}&select=id"
        )
        return result is not None

    async def get_hypothesis(self, idea_id: str) -> Optional[dict]:
        """Get hypothesis for idea."""
        return await self._query_single("hypotheses", f"idea_id=eq.{idea_id}&select=*")

    # ==================== Outcome Aggregates ====================

    async def outcome_exists(self, creative_id: str) -> bool:
        """Check if outcome aggregate exists for creative."""
        result = await self._query_single(
            "outcome_aggregates", f"creative_id=eq.{creative_id}&select=id"
        )
        return result is not None

    async def get_outcome(self, creative_id: str) -> Optional[dict]:
        """Get outcome aggregate for creative."""
        return await self._query_single(
            "outcome_aggregates",
            f"creative_id=eq.{creative_id}&select=*&order=created_at.desc",
        )

    async def outcome_is_processed(self, outcome_id: str) -> bool:
        """Check if outcome has been processed by learning loop."""
        result = await self._query_single(
            "outcome_aggregates", f"id=eq.{outcome_id}&select=learning_applied"
        )
        return result is not None and result.get("learning_applied") is True

    # ==================== Idea Confidence ====================

    async def get_current_confidence(self, idea_id: str) -> Optional[dict]:
        """Get latest confidence version for idea."""
        results = await self._query(
            "idea_confidence_versions",
            f"idea_id=eq.{idea_id}&select=*&order=version.desc&limit=1",
        )
        return results[0] if results else None

    # ==================== Raw Metrics ====================

    async def raw_metrics_exists(self, creative_id: str) -> bool:
        """Check if raw metrics exist for creative."""
        result = await self._query_single(
            "raw_metrics_current", f"creative_id=eq.{creative_id}&select=creative_id"
        )
        return result is not None

    # ==================== Daily Snapshots ====================

    async def snapshot_exists(self, creative_id: str, date: str) -> bool:
        """Check if daily snapshot exists for creative and date."""
        result = await self._query_single(
            "daily_metrics_snapshot",
            f"creative_id=eq.{creative_id}&snapshot_date=eq.{date}&select=id",
        )
        return result is not None

    # ==================== Events ====================

    async def event_emitted(self, event_type: str, entity_id: str) -> bool:
        """Check if event was emitted for entity."""
        result = await self._query_single(
            "event_log",
            f"event_type=eq.{event_type}&entity_id=eq.{entity_id}&select=id",
        )
        return result is not None

    async def get_events(self, entity_id: str, limit: int = 10) -> list[dict]:
        """Get events for entity."""
        return await self._query(
            "event_log",
            f"entity_id=eq.{entity_id}&select=*&order=created_at.desc&limit={limit}",
        )

    # ==================== Buyers ====================

    async def buyer_exists(self, telegram_id: str) -> bool:
        """Check if buyer exists by telegram_id."""
        result = await self._query_single(
            "buyers", f"telegram_id=eq.{telegram_id}&select=id"
        )
        return result is not None

    async def get_buyer(self, telegram_id: str) -> Optional[dict]:
        """Get buyer by telegram_id."""
        return await self._query_single(
            "buyers", f"telegram_id=eq.{telegram_id}&select=*"
        )

    # ==================== Cleanup ====================

    async def cleanup_test_data(self, prefix: str = "TEST_"):
        """
        Clean up test data by prefix.

        WARNING: Only use in test environment!
        """
        # Delete in reverse dependency order
        tables = [
            "hypothesis_deliveries",
            "hypotheses",
            "idea_confidence_versions",
            "outcome_aggregates",
            "decisions",
            "decision_traces",
            "ideas",
            "decomposed_creatives",
            "transcripts",
            "daily_metrics_snapshot",
            "raw_metrics_current",
            "creatives",
            "event_log",
        ]

        for table in tables:
            try:
                url = f"{self.base_url}/rest/v1/{table}?tracker_id=like.{prefix}*"
                await self.client.delete(url, headers=self.headers)
            except Exception:
                pass  # Table might not have tracker_id column


async def wait_for_condition(
    condition_fn,
    timeout: float = 60.0,
    interval: float = 2.0,
    message: str = "Condition not met",
) -> bool:
    """
    Wait for a condition to become true.

    Args:
        condition_fn: Async function returning bool
        timeout: Maximum wait time in seconds
        interval: Check interval in seconds
        message: Error message if timeout

    Returns:
        True if condition met, raises TimeoutError otherwise
    """
    elapsed = 0.0
    while elapsed < timeout:
        if await condition_fn():
            return True
        await asyncio.sleep(interval)
        elapsed += interval

    raise TimeoutError(f"{message} (timeout: {timeout}s)")
