"""
Recommendation Workflow

Daily recommendation generation and delivery workflow.
Replaces n8n workflows:
- wgEdEqt2BA3P9JlA (Daily Recommendation Generator)
- QC8bmnAYdH5mkntG (Recommendation Delivery)

Schedule: Daily at 09:00 UTC
"""

from datetime import timedelta
from dataclasses import dataclass
from typing import Optional, List

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from temporal.activities.recommendation import (
        get_active_buyers,
        generate_recommendation_for_buyer,
        send_recommendation_to_telegram,
        update_recommendation_delivery,
        emit_recommendation_event,
        check_existing_daily_recommendation,
    )


@dataclass
class DailyRecommendationInput:
    """Input for daily recommendation workflow"""
    # Optional: specific buyer_ids to process (empty = all active)
    buyer_ids: Optional[List[str]] = None
    # Skip buyers who already have today's recommendation
    skip_existing: bool = True
    # Maximum recommendations to generate (0 = unlimited)
    max_recommendations: int = 0


@dataclass
class DailyRecommendationResult:
    """Result of daily recommendation workflow"""
    total_buyers: int
    generated: int
    delivered: int
    skipped: int
    failed: int
    errors: List[str]


@dataclass
class SingleRecommendationInput:
    """Input for single recommendation delivery"""
    recommendation_id: str
    buyer_telegram_id: str
    buyer_name: str


@workflow.defn
class DailyRecommendationWorkflow:
    """
    Workflow for generating and delivering daily recommendations.

    Flow:
    1. Get all active buyers
    2. For each buyer:
       a. Check if already has today's recommendation
       b. Generate new recommendation
       c. Deliver via Telegram
       d. Update status and emit events
    """

    @workflow.run
    async def run(self, input: DailyRecommendationInput) -> DailyRecommendationResult:
        workflow.logger.info("Starting daily recommendation workflow")

        # Default retry policy
        retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=1),
            maximum_interval=timedelta(minutes=1),
            maximum_attempts=3,
        )

        # Step 1: Get active buyers
        if input.buyer_ids:
            # Use provided buyer IDs
            buyers = [{"id": bid} for bid in input.buyer_ids]
        else:
            # Fetch all active buyers
            buyers = await workflow.execute_activity(
                get_active_buyers,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=retry_policy,
            )

        workflow.logger.info(f"Processing {len(buyers)} buyers")

        result = DailyRecommendationResult(
            total_buyers=len(buyers),
            generated=0,
            delivered=0,
            skipped=0,
            failed=0,
            errors=[],
        )

        # Step 2: Process each buyer
        for buyer in buyers:
            buyer_id = buyer["id"]
            telegram_id = buyer.get("telegram_id")
            buyer_name = buyer.get("name", "Buyer")
            geo = buyer.get("geo")
            vertical = buyer.get("vertical")

            # Use first geo/vertical from arrays if available
            if not geo and buyer.get("geos"):
                geo = buyer["geos"][0]
            if not vertical and buyer.get("verticals"):
                vertical = buyer["verticals"][0]

            try:
                # Check if already has today's recommendation
                if input.skip_existing:
                    existing_id = await workflow.execute_activity(
                        check_existing_daily_recommendation,
                        buyer_id,
                        start_to_close_timeout=timedelta(seconds=10),
                        retry_policy=retry_policy,
                    )
                    if existing_id:
                        workflow.logger.info(
                            f"Skipping buyer {buyer_id}: already has recommendation {existing_id}"
                        )
                        result.skipped += 1
                        continue

                # Check limit
                if input.max_recommendations > 0 and result.generated >= input.max_recommendations:
                    workflow.logger.info(f"Reached max recommendations limit: {input.max_recommendations}")
                    result.skipped += len(buyers) - (result.generated + result.failed + result.skipped)
                    break

                # Generate recommendation
                recommendation = await workflow.execute_activity(
                    generate_recommendation_for_buyer,
                    args=[buyer_id, geo, vertical],
                    start_to_close_timeout=timedelta(seconds=60),
                    retry_policy=retry_policy,
                )

                recommendation_id = recommendation["id"]
                result.generated += 1

                # Emit generation event
                await workflow.execute_activity(
                    emit_recommendation_event,
                    args=[recommendation_id, buyer_id, "RecommendationGenerated"],
                    start_to_close_timeout=timedelta(seconds=10),
                    retry_policy=retry_policy,
                )

                # Deliver via Telegram (if has telegram_id)
                if telegram_id:
                    delivery_result = await workflow.execute_activity(
                        send_recommendation_to_telegram,
                        args=[
                            recommendation_id,
                            telegram_id,
                            buyer_name,
                            recommendation["description"],
                            recommendation["mode"],
                            recommendation["avg_confidence"],
                            recommendation.get("components", []),
                        ],
                        start_to_close_timeout=timedelta(seconds=30),
                        retry_policy=retry_policy,
                    )

                    # Update delivery status
                    await workflow.execute_activity(
                        update_recommendation_delivery,
                        args=[
                            recommendation_id,
                            delivery_result.get("message_id"),
                            "delivered",
                        ],
                        start_to_close_timeout=timedelta(seconds=10),
                        retry_policy=retry_policy,
                    )

                    # Emit delivery event
                    await workflow.execute_activity(
                        emit_recommendation_event,
                        args=[recommendation_id, buyer_id, "RecommendationDelivered"],
                        start_to_close_timeout=timedelta(seconds=10),
                        retry_policy=retry_policy,
                    )

                    result.delivered += 1
                    workflow.logger.info(
                        f"Delivered recommendation {recommendation_id} to buyer {buyer_id}"
                    )
                else:
                    workflow.logger.warning(
                        f"Buyer {buyer_id} has no telegram_id, skipping delivery"
                    )

            except Exception as e:
                error_msg = f"Failed to process buyer {buyer_id}: {str(e)}"
                workflow.logger.error(error_msg)
                result.failed += 1
                result.errors.append(error_msg)

        workflow.logger.info(
            f"Daily recommendation workflow complete: "
            f"generated={result.generated}, delivered={result.delivered}, "
            f"skipped={result.skipped}, failed={result.failed}"
        )

        return result


@workflow.defn
class SingleRecommendationDeliveryWorkflow:
    """
    Workflow for delivering a single recommendation.

    Used when a recommendation was generated but not delivered
    (e.g., Telegram was unavailable).
    """

    @workflow.run
    async def run(self, input: SingleRecommendationInput) -> dict:
        workflow.logger.info(f"Delivering recommendation {input.recommendation_id}")

        retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=1),
            maximum_interval=timedelta(minutes=1),
            maximum_attempts=3,
        )

        # Get recommendation details
        from temporal.activities.recommendation import get_recommendation_by_id

        recommendation = await workflow.execute_activity(
            get_recommendation_by_id,
            input.recommendation_id,
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=retry_policy,
        )

        if not recommendation:
            raise ValueError(f"Recommendation {input.recommendation_id} not found")

        # Send to Telegram
        delivery_result = await workflow.execute_activity(
            send_recommendation_to_telegram,
            args=[
                input.recommendation_id,
                input.buyer_telegram_id,
                input.buyer_name,
                recommendation.get("description", ""),
                recommendation.get("mode", "exploitation"),
                recommendation.get("avg_confidence", 0.0),
                [],  # Components are in recommended_components JSON
            ],
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=retry_policy,
        )

        # Update status
        await workflow.execute_activity(
            update_recommendation_delivery,
            args=[
                input.recommendation_id,
                delivery_result.get("message_id"),
                "delivered",
            ],
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=retry_policy,
        )

        # Emit event
        await workflow.execute_activity(
            emit_recommendation_event,
            args=[
                input.recommendation_id,
                recommendation.get("buyer_id", ""),
                "RecommendationDelivered",
            ],
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=retry_policy,
        )

        return {
            "recommendation_id": input.recommendation_id,
            "message_id": delivery_result.get("message_id"),
            "status": "delivered",
        }
