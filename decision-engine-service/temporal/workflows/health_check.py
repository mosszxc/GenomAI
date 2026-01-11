"""
Health Check Workflow

Periodic health monitoring for GenomAI.
Part of Hygiene Agent system.

Schedule: Every 3 hours
Tasks:
- Check Supabase connection
- Check table sizes
- Check pending counts
- Compute health score
- Send alerts if needed
- Save report
"""

from dataclasses import dataclass, field
from datetime import timedelta
from typing import List, Dict, Optional

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from temporal.activities.hygiene_health import (
        check_supabase_connection,
        get_table_sizes,
        get_pending_counts,
        send_admin_alert,
        save_hygiene_report,
        format_health_alert,
    )


@dataclass
class HealthCheckInput:
    """Input for HealthCheckWorkflow."""

    check_supabase: bool = True
    check_table_sizes: bool = True
    check_pending: bool = True
    alert_on_warning: bool = True
    alert_on_critical: bool = True
    critical_threshold: float = 0.5
    warning_threshold: float = 0.8


@dataclass
class HealthCheckResult:
    """Result of HealthCheckWorkflow."""

    health_score: float = 1.0
    supabase_ok: bool = True
    supabase_latency_ms: Optional[float] = None
    temporal_ok: bool = True  # If workflow runs, temporal is OK
    table_sizes: Dict[str, int] = field(default_factory=dict)
    pending_counts: Dict[str, int] = field(default_factory=dict)
    issues: List[str] = field(default_factory=list)
    alerts_sent: int = 0
    completed_at: str = ""


@workflow.defn
class HealthCheckWorkflow:
    """
    Workflow for periodic health monitoring.

    Flow:
    1. Check Supabase connection
    2. Get table sizes
    3. Get pending counts
    4. Compute health score
    5. Send alerts if thresholds exceeded
    6. Save report
    """

    @workflow.run
    async def run(self, input: HealthCheckInput) -> HealthCheckResult:
        workflow.logger.info("Starting health check workflow")

        retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=1),
            maximum_interval=timedelta(minutes=1),
            maximum_attempts=3,
        )

        result = HealthCheckResult()

        # Step 1: Check Supabase connection
        if input.check_supabase:
            try:
                sb_result = await workflow.execute_activity(
                    check_supabase_connection,
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=retry_policy,
                )
                result.supabase_ok = sb_result.get("connected", False)
                result.supabase_latency_ms = sb_result.get("latency_ms")

                if not result.supabase_ok:
                    result.issues.append(
                        f"Supabase connection failed: {sb_result.get('error', 'unknown')}"
                    )
                elif result.supabase_latency_ms and result.supabase_latency_ms > 3000:
                    result.issues.append(
                        f"Supabase slow: {result.supabase_latency_ms:.0f}ms"
                    )

            except Exception as e:
                workflow.logger.error(f"Supabase check failed: {e}")
                result.supabase_ok = False
                result.issues.append(f"Supabase check error: {e}")

        # Step 2: Get table sizes
        if input.check_table_sizes:
            try:
                result.table_sizes = await workflow.execute_activity(
                    get_table_sizes,
                    start_to_close_timeout=timedelta(seconds=60),
                    retry_policy=retry_policy,
                )
            except Exception as e:
                workflow.logger.error(f"Table sizes check failed: {e}")
                result.issues.append(f"Table sizes error: {e}")

        # Step 3: Get pending counts
        if input.check_pending:
            try:
                result.pending_counts = await workflow.execute_activity(
                    get_pending_counts,
                    start_to_close_timeout=timedelta(seconds=60),
                    retry_policy=retry_policy,
                )

                # Check for backlog
                total_pending = sum(result.pending_counts.values())
                if total_pending > 100:
                    result.issues.append(
                        f"Large pending backlog: {total_pending} items"
                    )
                elif total_pending > 50:
                    result.issues.append(
                        f"Moderate pending backlog: {total_pending} items"
                    )

            except Exception as e:
                workflow.logger.error(f"Pending counts check failed: {e}")
                result.issues.append(f"Pending counts error: {e}")

        # Step 4: Compute health score
        result.health_score = self._compute_health_score(result)
        workflow.logger.info(f"Health score: {result.health_score:.2f}")

        # Step 5: Send alerts if needed
        alert_severity = None
        if result.health_score < input.critical_threshold:
            alert_severity = "critical"
        elif result.health_score < input.warning_threshold:
            alert_severity = "warning"

        if alert_severity:
            should_alert = (
                alert_severity == "critical" and input.alert_on_critical
            ) or (alert_severity == "warning" and input.alert_on_warning)

            if should_alert:
                try:
                    alert_body = format_health_alert(
                        result.health_score,
                        result.supabase_ok,
                        result.temporal_ok,
                        result.issues,
                    )

                    sent = await workflow.execute_activity(
                        send_admin_alert,
                        args=[alert_severity, "GenomAI Health Check", alert_body],
                        start_to_close_timeout=timedelta(seconds=30),
                        retry_policy=retry_policy,
                    )

                    if sent:
                        result.alerts_sent += 1
                        workflow.logger.info(f"Sent {alert_severity} alert")

                except Exception as e:
                    workflow.logger.error(f"Failed to send alert: {e}")

        # Step 6: Save report
        result.completed_at = workflow.now().isoformat()

        try:
            report_data = {
                "report_type": "health_check",
                "health_score": result.health_score,
                "supabase_connected": result.supabase_ok,
                "supabase_latency_ms": result.supabase_latency_ms,
                "temporal_connected": result.temporal_ok,
                "table_sizes": result.table_sizes,
                "pending_counts": result.pending_counts,
                "integrity_issues": [{"issue": i} for i in result.issues],
                "alerts_sent": result.alerts_sent,
                "workflow_id": workflow.info().workflow_id,
            }

            await workflow.execute_activity(
                save_hygiene_report,
                args=[report_data],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=retry_policy,
            )

        except Exception as e:
            workflow.logger.error(f"Failed to save report: {e}")

        workflow.logger.info(
            f"Health check complete: score={result.health_score:.2f}, "
            f"issues={len(result.issues)}, alerts={result.alerts_sent}"
        )

        return result

    def _compute_health_score(self, result: HealthCheckResult) -> float:
        """Compute weighted health score."""
        score = 1.0

        # Connection failures are critical
        if not result.supabase_ok:
            score -= 0.5
        if not result.temporal_ok:
            score -= 0.3

        # High latency reduces score
        if result.supabase_latency_ms and result.supabase_latency_ms > 3000:
            score -= 0.1

        # Large pending backlog reduces score
        total_pending = sum(result.pending_counts.values())
        if total_pending > 100:
            score -= 0.1
        elif total_pending > 50:
            score -= 0.05

        # Each issue reduces score slightly
        score -= len(result.issues) * 0.02

        return max(0.0, min(1.0, score))
