"""
Outcome Service — Aggregates outcomes from daily snapshots

Replaces Outcome Aggregator n8n workflow with Python API.
"""

import os
import statistics
from datetime import datetime, date
from dataclasses import dataclass
from typing import Optional, List
from decimal import Decimal
import httpx

from src.utils.errors import SupabaseError


# Schema name for all operations
SCHEMA = "genomai"


@dataclass
class OutcomeAggregate:
    """Represents an aggregated outcome"""

    id: Optional[str] = None
    creative_id: str = ""
    decision_id: str = ""
    window_id: str = ""
    window_start: date = None
    window_end: date = None
    conversions: int = 0
    spend: Decimal = Decimal("0")
    cpa: Optional[Decimal] = None
    trend: Optional[str] = None
    volatility: Optional[Decimal] = None
    origin_type: str = "system"
    learning_applied: bool = False

    def to_dict(self) -> dict:
        """Convert to dictionary for API response"""
        return {
            "id": self.id,
            "creative_id": self.creative_id,
            "decision_id": self.decision_id,
            "window_id": self.window_id,
            "window_start": str(self.window_start) if self.window_start else None,
            "window_end": str(self.window_end) if self.window_end else None,
            "conversions": self.conversions,
            "spend": float(self.spend) if self.spend else 0,
            "cpa": float(self.cpa) if self.cpa else None,
            "trend": self.trend,
            "volatility": float(self.volatility) if self.volatility else None,
            "origin_type": self.origin_type,
            "learning_applied": self.learning_applied,
        }


@dataclass
class AggregateResult:
    """Result of outcome aggregation"""

    success: bool
    outcome: Optional[OutcomeAggregate] = None
    learning_triggered: bool = False
    skipped: bool = False  # True when tracker has no linked idea (expected case)
    error_code: Optional[str] = None
    error_message: Optional[str] = None


class OutcomeService:
    """
    Service for aggregating outcomes from daily snapshots.

    Flow:
    1. Load snapshot data
    2. Find idea via creative_idea_lookup
    3. Find APPROVE decision for idea
    4. Calculate window ID
    5. Insert outcome_aggregate
    6. Trigger Learning Loop
    """

    def __init__(self):
        self.rest_url, self.supabase_key = self._get_credentials()

    def _get_credentials(self):
        """Get Supabase credentials from environment"""
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        if not supabase_url or not supabase_key:
            raise SupabaseError("Missing Supabase credentials")

        rest_url = f"{supabase_url}/rest/v1"
        return rest_url, supabase_key

    def _get_headers(self, for_write: bool = False) -> dict:
        """Get headers for Supabase REST API with schema"""
        headers = {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
            "Accept-Profile": SCHEMA,
            "Content-Type": "application/json",
        }
        if for_write:
            headers["Content-Profile"] = SCHEMA
            headers["Prefer"] = "return=representation"
        return headers

    @staticmethod
    def calculate_window_id(decision_date: date, snapshot_date: date) -> str:
        """
        Calculate window ID based on days since decision.

        Args:
            decision_date: Date of the APPROVE decision
            snapshot_date: Date of the snapshot

        Returns:
            str: Window ID (D1, D3, D7, D7+)
        """
        days_diff = (snapshot_date - decision_date).days

        if days_diff <= 1:
            return "D1"
        elif days_diff <= 3:
            return "D3"
        elif days_diff <= 7:
            return "D7"
        else:
            return "D7+"

    @staticmethod
    def calculate_cpa(spend: Decimal, conversions: int) -> Optional[Decimal]:
        """
        Calculate CPA (Cost Per Acquisition).

        Args:
            spend: Total spend
            conversions: Total conversions

        Returns:
            Decimal: CPA or None if conversions is 0
        """
        if conversions == 0:
            return None
        return spend / Decimal(conversions)

    @staticmethod
    def calculate_trend(
        current_cpa: Optional[Decimal], previous_cpa: Optional[Decimal]
    ) -> Optional[str]:
        """
        Calculate trend based on CPA change.

        Args:
            current_cpa: Current CPA value
            previous_cpa: Previous CPA value

        Returns:
            "improving" - CPA decreased (better)
            "declining" - CPA increased (worse)
            "stable" - change < 10%
            None - if either CPA is None
        """
        if current_cpa is None or previous_cpa is None:
            return None

        if previous_cpa == 0:
            return None

        change_ratio = (current_cpa - previous_cpa) / previous_cpa

        if change_ratio < Decimal("-0.1"):
            return "improving"
        elif change_ratio > Decimal("0.1"):
            return "declining"
        else:
            return "stable"

    @staticmethod
    def calculate_volatility(cpa_values: List[Decimal]) -> Optional[Decimal]:
        """
        Calculate volatility as coefficient of variation (CV).

        CV = std_dev / mean

        Args:
            cpa_values: List of CPA values (at least 2 required)

        Returns:
            Decimal: Volatility coefficient (0.0 - 1.0+) or None if insufficient data

        Interpretation:
            < 0.1: low volatility (stable)
            0.1-0.3: medium volatility
            > 0.3: high volatility (unstable)
        """
        if len(cpa_values) < 2:
            return None

        # Filter out None values and convert to float for statistics
        float_values = [float(v) for v in cpa_values if v is not None]

        if len(float_values) < 2:
            return None

        mean = statistics.mean(float_values)
        if mean == 0:
            return None

        std_dev = statistics.stdev(float_values)
        cv = std_dev / mean

        return Decimal(str(round(cv, 4)))

    async def get_snapshot(self, snapshot_id: str) -> Optional[dict]:
        """Load snapshot from daily_metrics_snapshot"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.rest_url}/daily_metrics_snapshot?id=eq.{snapshot_id}&select=*",
                headers=self._get_headers(),
            )
            response.raise_for_status()
            data = response.json()
            return data[0] if data else None

    async def get_idea_by_tracker(self, tracker_id: str) -> Optional[dict]:
        """Find idea via creative_idea_lookup"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.rest_url}/creative_idea_lookup?tracker_id=eq.{tracker_id}&select=*",
                headers=self._get_headers(),
            )
            response.raise_for_status()
            data = response.json()
            return data[0] if data else None

    async def get_approve_decision(self, idea_id: str) -> Optional[dict]:
        """Find APPROVE decision for idea"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.rest_url}/decisions?idea_id=eq.{idea_id}&decision=ilike.approve&select=*&order=created_at.desc&limit=1",
                headers=self._get_headers(),
            )
            response.raise_for_status()
            data = response.json()
            return data[0] if data else None

    async def get_previous_outcome(self, creative_id: str) -> Optional[dict]:
        """
        Get the most recent outcome for a creative to calculate trend.

        Args:
            creative_id: UUID of the creative

        Returns:
            Previous outcome record or None
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.rest_url}/outcome_aggregates?creative_id=eq.{creative_id}&select=cpa,created_at&order=created_at.desc&limit=1",
                headers=self._get_headers(),
            )
            response.raise_for_status()
            data = response.json()
            return data[0] if data else None

    async def get_historical_cpa(
        self, creative_id: str, lookback_days: int = 7
    ) -> List[Decimal]:
        """
        Get historical CPA values for volatility calculation.

        Args:
            creative_id: UUID of the creative
            lookback_days: Number of days to look back (default 7)

        Returns:
            List of CPA values (may be empty)
        """
        from datetime import timedelta

        cutoff_date = (datetime.now() - timedelta(days=lookback_days)).isoformat()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.rest_url}/outcome_aggregates?creative_id=eq.{creative_id}&created_at=gte.{cutoff_date}&select=cpa&order=created_at.desc",
                headers=self._get_headers(),
            )
            response.raise_for_status()
            data = response.json()

            cpa_values = []
            for record in data:
                if record.get("cpa") is not None:
                    cpa_values.append(Decimal(str(record["cpa"])))

            return cpa_values

    async def upsert_outcome(self, outcome: OutcomeAggregate) -> dict:
        """
        Upsert outcome aggregate into database.

        Uses ON CONFLICT (creative_id, window_start, window_end) DO UPDATE
        to handle duplicate key constraint gracefully.
        """
        payload = {
            "creative_id": outcome.creative_id,
            "decision_id": outcome.decision_id,
            "window_id": outcome.window_id,
            "window_start": str(outcome.window_start),
            "window_end": str(outcome.window_end),
            "conversions": outcome.conversions,
            "spend": float(outcome.spend),
            "cpa": float(outcome.cpa) if outcome.cpa else None,
            "trend": outcome.trend,
            "volatility": float(outcome.volatility) if outcome.volatility else None,
            "origin_type": outcome.origin_type,
            "learning_applied": outcome.learning_applied,
        }

        headers = self._get_headers(for_write=True)
        # Use resolution=merge-duplicates for UPSERT behavior
        headers["Prefer"] = "return=representation,resolution=merge-duplicates"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.rest_url}/outcome_aggregates",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data[0] if data else {}

    async def emit_event(
        self,
        outcome_id: str,
        decision_id: str,
        idea_id: str,
        conversions: int,
        window_id: str,
    ) -> None:
        """Emit OutcomeAggregated event to event_log"""
        import json

        payload = {
            "event_type": "OutcomeAggregated",
            "entity_type": "outcome",
            "entity_id": outcome_id,
            "payload": json.dumps(
                {
                    "outcome_id": outcome_id,
                    "decision_id": decision_id,
                    "idea_id": idea_id,
                    "conversions": conversions,
                    "window_id": window_id,
                }
            ),
            "occurred_at": datetime.now().isoformat(),
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.rest_url}/event_log",
                headers=self._get_headers(for_write=True),
                json=payload,
            )
            response.raise_for_status()

    async def trigger_learning_loop(
        self,
        outcome_id: str,
        decision_id: str,
        idea_id: str,
        conversions: int,
        origin_type: str = "system",
    ) -> bool:
        """Call Learning Loop v2 webhook"""

        learning_loop_url = "https://kazamaqwe.app.n8n.cloud/webhook/learning-loop-v2"

        payload = {
            "outcome_id": outcome_id,
            "decision_id": decision_id,
            "idea_id": idea_id,
            "conversions": conversions,
            "origin_type": origin_type,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(learning_loop_url, json=payload)
                return response.status_code == 200
        except Exception:
            # Don't fail if learning loop is unavailable
            return False

    async def aggregate(self, snapshot_id: str) -> AggregateResult:
        """
        Aggregate outcome from snapshot.

        Args:
            snapshot_id: UUID of the daily_metrics_snapshot

        Returns:
            AggregateResult with outcome or error
        """
        try:
            # 1. Load snapshot
            snapshot = await self.get_snapshot(snapshot_id)
            if not snapshot:
                return AggregateResult(
                    success=False,
                    error_code="SNAPSHOT_NOT_FOUND",
                    error_message=f"Snapshot {snapshot_id} not found",
                )

            tracker_id = snapshot.get("tracker_id")
            snapshot_date_str = snapshot.get("date")
            metrics = snapshot.get("metrics", {})

            # Parse snapshot date
            if isinstance(snapshot_date_str, str):
                snapshot_date = date.fromisoformat(snapshot_date_str)
            else:
                snapshot_date = snapshot_date_str

            # 2. Find idea via lookup
            idea_lookup = await self.get_idea_by_tracker(tracker_id)
            if not idea_lookup or not idea_lookup.get("idea_id"):
                # Tracker without linked idea is expected case (e.g., test campaigns)
                # Return success=True with skipped=True to avoid polluting error logs
                return AggregateResult(
                    success=True,
                    skipped=True,
                    error_code="IDEA_NOT_FOUND",
                    error_message=f"No idea found for tracker {tracker_id}",
                )

            idea_id = idea_lookup["idea_id"]
            creative_id = idea_lookup.get("creative_id")

            # 3. Find APPROVE decision
            decision = await self.get_approve_decision(idea_id)
            if not decision:
                return AggregateResult(
                    success=False,
                    error_code="NO_APPROVED_DECISION",
                    error_message=f"No APPROVE decision found for idea {idea_id}",
                )

            decision_id = decision["id"]
            decision_created_at = decision.get("created_at", "")

            # Parse decision date
            if isinstance(decision_created_at, str):
                decision_date = date.fromisoformat(decision_created_at.split("T")[0])
            else:
                decision_date = decision_created_at

            # 4. Calculate window ID
            window_id = self.calculate_window_id(decision_date, snapshot_date)

            # 5. Extract metrics
            conversions = metrics.get("conversions", 0) or 0
            spend = Decimal(str(metrics.get("cost", 0) or 0))

            # Calculate CPA
            cpa = self.calculate_cpa(spend, conversions)

            # Calculate trend by comparing with previous outcome
            previous_outcome = await self.get_previous_outcome(creative_id)
            previous_cpa = None
            if previous_outcome and previous_outcome.get("cpa") is not None:
                previous_cpa = Decimal(str(previous_outcome["cpa"]))
            trend = self.calculate_trend(cpa, previous_cpa)

            # Calculate volatility from historical CPA values
            historical_cpa = await self.get_historical_cpa(creative_id)
            # Include current CPA in volatility calculation
            if cpa is not None:
                historical_cpa.insert(0, cpa)
            volatility = self.calculate_volatility(historical_cpa)

            # 6. Create and insert outcome
            outcome = OutcomeAggregate(
                creative_id=creative_id,
                decision_id=decision_id,
                window_id=window_id,
                window_start=decision_date,
                window_end=snapshot_date,
                conversions=conversions,
                spend=spend,
                cpa=cpa,
                trend=trend,
                volatility=volatility,
                origin_type="system",
                learning_applied=False,
            )

            inserted = await self.upsert_outcome(outcome)
            outcome.id = inserted.get("id")

            # 7. Emit event
            await self.emit_event(
                outcome_id=outcome.id,
                decision_id=decision_id,
                idea_id=idea_id,
                conversions=conversions,
                window_id=window_id,
            )

            # 8. Trigger Learning Loop
            learning_triggered = await self.trigger_learning_loop(
                outcome_id=outcome.id,
                decision_id=decision_id,
                idea_id=idea_id,
                conversions=conversions,
                origin_type="system",
            )

            return AggregateResult(
                success=True, outcome=outcome, learning_triggered=learning_triggered
            )

        except httpx.HTTPStatusError as e:
            return AggregateResult(
                success=False,
                error_code="DATABASE_ERROR",
                error_message=f"Database error: {e.response.text}",
            )
        except Exception as e:
            return AggregateResult(
                success=False, error_code="INTERNAL_ERROR", error_message=str(e)
            )


# Singleton instance
_service_instance: Optional[OutcomeService] = None


def get_outcome_service() -> OutcomeService:
    """Get or create singleton OutcomeService instance"""
    global _service_instance
    if _service_instance is None:
        _service_instance = OutcomeService()
    return _service_instance
