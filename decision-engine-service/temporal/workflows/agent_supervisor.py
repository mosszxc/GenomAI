"""
Agent Supervisor Workflow

Temporal workflow for supervising multi-agent task distribution.

Tasks:
- Poll pending GitHub issues (optionally)
- Process pending tasks from queue
- Assign tasks to available agents using smart assignment
- Monitor agent health (orphan detection)

Schedule: Every 5 minutes

Issue: #351 - Multi-Agent Orchestration Phase 3
"""

from datetime import timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Any

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from temporal.activities.agent_supervisor import (
        get_pending_github_issues,
        get_pending_tasks_from_queue,
        get_available_agents,
        add_task_to_queue,
        assign_task_to_agent,
        release_orphaned_agents,
    )


@dataclass
class AgentSupervisorInput:
    """Input for agent supervisor workflow."""

    # Poll GitHub for new issues (adds to queue if not present)
    poll_github: bool = True
    # Labels to filter GitHub issues
    github_labels: List[str] = field(default_factory=lambda: ["enhancement"])
    # Maximum issues to fetch from GitHub
    github_limit: int = 10
    # Process pending tasks from queue
    process_queue: bool = True
    # Maximum tasks to process per run
    max_assignments: int = 5
    # Run orphan detection
    run_orphan_detection: bool = True
    # Orphan timeout in minutes
    orphan_timeout_minutes: int = 10


@dataclass
class AgentSupervisorResult:
    """Result of agent supervisor workflow."""

    # GitHub issues found
    github_issues_found: int = 0
    # Tasks added to queue
    tasks_added: int = 0
    # Tasks successfully assigned
    tasks_assigned: int = 0
    # Tasks that couldn't be assigned (no agents)
    tasks_pending: int = 0
    # Orphaned agents released
    orphaned_agents: int = 0
    # Assignment details
    assignments: List[Dict[str, Any]] = field(default_factory=list)
    # Errors encountered
    errors: List[str] = field(default_factory=list)
    # Timestamp
    completed_at: str = ""


@workflow.defn
class AgentSupervisorWorkflow:
    """
    Workflow for supervising multi-agent task distribution.

    Flow:
    1. Poll GitHub for pending issues (optional)
    2. Add new issues to task queue
    3. Get pending tasks from queue
    4. Get available agents
    5. Assign tasks to agents using smart assignment
    6. Release orphaned agents
    7. Emit stats

    This workflow runs periodically (every 5 minutes) to ensure
    tasks are distributed to available agents.
    """

    @workflow.run
    async def run(self, input: AgentSupervisorInput) -> AgentSupervisorResult:
        workflow.logger.info("Starting Agent Supervisor workflow")

        retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=1),
            maximum_interval=timedelta(minutes=1),
            maximum_attempts=3,
        )

        result = AgentSupervisorResult()

        # Step 1: Poll GitHub for new issues (optional)
        if input.poll_github:
            try:
                github_issues = await workflow.execute_activity(
                    get_pending_github_issues,
                    args=[input.github_labels, input.github_limit],
                    start_to_close_timeout=timedelta(seconds=60),
                    retry_policy=retry_policy,
                )
                result.github_issues_found = len(github_issues)
                workflow.logger.info(f"Found {len(github_issues)} GitHub issues")

                # Add new issues to queue
                for issue in github_issues:
                    try:
                        added = await workflow.execute_activity(
                            add_task_to_queue,
                            args=[
                                issue["number"],
                                issue["title"],
                                0,  # priority
                                issue.get("labels", []),
                            ],
                            start_to_close_timeout=timedelta(seconds=30),
                            retry_policy=retry_policy,
                        )
                        if added:
                            result.tasks_added += 1
                    except Exception as e:
                        workflow.logger.warning(
                            f"Failed to add issue #{issue['number']} to queue: {e}"
                        )
            except Exception as e:
                workflow.logger.error(f"Failed to poll GitHub: {e}")
                result.errors.append(f"GitHub poll error: {e}")

        # Step 2: Get pending tasks from queue
        pending_tasks = []
        if input.process_queue:
            try:
                pending_tasks = await workflow.execute_activity(
                    get_pending_tasks_from_queue,
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=retry_policy,
                )
                workflow.logger.info(f"Found {len(pending_tasks)} pending tasks")
            except Exception as e:
                workflow.logger.error(f"Failed to get pending tasks: {e}")
                result.errors.append(f"Queue fetch error: {e}")

        # Step 3: Get available agents
        available_agents = []
        if pending_tasks:
            try:
                available_agents = await workflow.execute_activity(
                    get_available_agents,
                    args=[None],  # No specialization filter
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=retry_policy,
                )
                workflow.logger.info(f"Found {len(available_agents)} available agents")
            except Exception as e:
                workflow.logger.error(f"Failed to get available agents: {e}")
                result.errors.append(f"Agent fetch error: {e}")

        # Step 4: Assign tasks to agents
        assignments_made = 0
        for task in pending_tasks[: input.max_assignments]:
            if not available_agents:
                workflow.logger.info("No available agents, stopping assignments")
                result.tasks_pending = len(pending_tasks) - assignments_made
                break

            # Determine required specialization from labels
            labels = task.get("labels", [])
            specialization = None
            for label in labels:
                if label in ["temporal", "migration", "api", "telegram", "keitaro"]:
                    specialization = label
                    break

            try:
                assignment = await workflow.execute_activity(
                    assign_task_to_agent,
                    args=[task["issue_number"], specialization],
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=retry_policy,
                )
                result.assignments.append(assignment)

                if assignment.get("success"):
                    assignments_made += 1
                    result.tasks_assigned += 1
                    workflow.logger.info(
                        f"Assigned task #{task['issue_number']} to {assignment.get('agent_id')}"
                    )
                    # Remove agent from available list (now busy)
                    available_agents = [
                        a
                        for a in available_agents
                        if a.get("agent_id") != assignment.get("agent_id")
                    ]
                else:
                    result.tasks_pending += 1
                    workflow.logger.info(
                        f"Could not assign task #{task['issue_number']}: {assignment.get('reason')}"
                    )
            except Exception as e:
                workflow.logger.error(
                    f"Assignment error for #{task['issue_number']}: {e}"
                )
                result.errors.append(f"Assignment error #{task['issue_number']}: {e}")

        # Step 5: Release orphaned agents
        if input.run_orphan_detection:
            try:
                orphaned = await workflow.execute_activity(
                    release_orphaned_agents,
                    input.orphan_timeout_minutes,
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=retry_policy,
                )
                result.orphaned_agents = orphaned
                if orphaned > 0:
                    workflow.logger.warning(f"Released {orphaned} orphaned agents")
            except Exception as e:
                workflow.logger.error(f"Orphan detection error: {e}")
                result.errors.append(f"Orphan detection error: {e}")

        # Set completion time
        result.completed_at = workflow.now().isoformat()

        workflow.logger.info(
            f"Agent Supervisor complete: github={result.github_issues_found}, "
            f"added={result.tasks_added}, assigned={result.tasks_assigned}, "
            f"pending={result.tasks_pending}, orphaned={result.orphaned_agents}"
        )

        return result
