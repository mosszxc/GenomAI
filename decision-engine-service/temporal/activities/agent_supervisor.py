"""
Agent Supervisor Activities

Activities for the AgentSupervisorWorkflow:
- Polling pending issues from GitHub
- Getting available agents
- Assigning tasks to agents
- Agent registration/unregistration

Issue: #351 - Multi-Agent Orchestration Phase 3
"""

import logging
import os
import subprocess
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from temporalio import activity

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class GitHubIssue:
    """GitHub issue data."""

    number: int
    title: str
    labels: List[str]
    state: str


@dataclass
class Agent:
    """Agent data."""

    agent_id: str
    hostname: str
    specializations: List[str]
    last_heartbeat: str


@dataclass
class TaskAssignment:
    """Task assignment result."""

    issue_number: int
    agent_id: Optional[str]
    success: bool
    reason: str


def get_supabase_client():
    """Get Supabase client for database operations."""
    from supabase import create_client

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")

    return create_client(url, key)


@activity.defn
async def get_pending_github_issues(
    labels: Optional[List[str]] = None,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """
    Get pending GitHub issues that need to be assigned.

    Uses 'gh' CLI to fetch open issues.

    Args:
        labels: Filter by labels (e.g., ["enhancement", "bug"])
        limit: Maximum number of issues to return

    Returns:
        List of issue dictionaries with number, title, labels
    """
    activity.logger.info(f"Fetching pending GitHub issues (limit={limit})")

    try:
        # Build gh command
        cmd = [
            "gh",
            "issue",
            "list",
            "--state",
            "open",
            "--json",
            "number,title,labels",
        ]
        if labels:
            cmd.extend(["--label", ",".join(labels)])
        cmd.extend(["--limit", str(limit)])

        # Execute gh command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            activity.logger.error(f"gh command failed: {result.stderr}")
            return []

        import json

        issues = json.loads(result.stdout)

        # Transform to simpler format
        return [
            {
                "number": issue["number"],
                "title": issue["title"],
                "labels": [label["name"] for label in issue.get("labels", [])],
            }
            for issue in issues
        ]
    except subprocess.TimeoutExpired:
        activity.logger.error("gh command timed out")
        return []
    except Exception as e:
        activity.logger.error(f"Failed to fetch issues: {e}")
        return []


@activity.defn
async def get_pending_tasks_from_queue() -> List[Dict[str, Any]]:
    """
    Get pending tasks from the Supabase agent_tasks queue.

    Returns:
        List of pending task dictionaries
    """
    activity.logger.info("Fetching pending tasks from queue")

    try:
        client = get_supabase_client()

        result = (
            client.schema("genomai")
            .table("agent_tasks")
            .select("issue_number, issue_title, priority, labels, created_at")
            .eq("status", "pending")
            .order("priority", desc=True)
            .order("created_at", desc=False)
            .limit(20)
            .execute()
        )

        return result.data or []
    except Exception as e:
        activity.logger.error(f"Failed to fetch pending tasks: {e}")
        return []


@activity.defn
async def get_available_agents(
    specialization: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Get available agents (online, not busy).

    Args:
        specialization: Optional filter by specialization

    Returns:
        List of available agent dictionaries
    """
    activity.logger.info(f"Fetching available agents (specialization={specialization})")

    try:
        client = get_supabase_client()

        # Call the get_available_agents RPC function
        result = client.rpc(
            "get_available_agents",
            {"p_specialization": specialization},
        ).execute()

        return result.data or []
    except Exception as e:
        activity.logger.error(f"Failed to fetch available agents: {e}")
        return []


@activity.defn
async def add_task_to_queue(
    issue_number: int,
    title: Optional[str] = None,
    priority: int = 0,
    labels: Optional[List[str]] = None,
) -> bool:
    """
    Add a task to the agent queue.

    Args:
        issue_number: GitHub issue number
        title: Issue title (optional, will fetch from GitHub if not provided)
        priority: Task priority (higher = more urgent)
        labels: Issue labels for smart assignment

    Returns:
        True if task was added, False if already exists or failed
    """
    activity.logger.info(f"Adding task #{issue_number} to queue")

    try:
        client = get_supabase_client()

        # If no title, try to get from GitHub
        if not title:
            try:
                result = subprocess.run(
                    ["gh", "issue", "view", str(issue_number), "--json", "title"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    import json

                    data = json.loads(result.stdout)
                    title = data.get("title", f"Issue #{issue_number}")
            except Exception:
                title = f"Issue #{issue_number}"

        # Insert into queue
        result = (
            client.schema("genomai")
            .table("agent_tasks")
            .upsert(
                {
                    "issue_number": issue_number,
                    "issue_title": title,
                    "priority": priority,
                    "labels": labels or [],
                    "status": "pending",
                },
                on_conflict="issue_number",
            )
            .execute()
        )

        activity.logger.info(f"Task #{issue_number} added to queue")
        return True
    except Exception as e:
        activity.logger.error(f"Failed to add task: {e}")
        return False


@activity.defn
async def assign_task_to_agent(
    issue_number: int,
    required_specialization: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Assign a task to the best available agent using smart assignment.

    Args:
        issue_number: Issue number to assign
        required_specialization: Optional specialization requirement

    Returns:
        Dictionary with assignment result (agent_id, success, reason)
    """
    activity.logger.info(
        f"Assigning task #{issue_number} (specialization={required_specialization})"
    )

    try:
        client = get_supabase_client()

        # Call the smart assignment RPC function
        result = client.rpc(
            "assign_task_to_agent",
            {
                "p_issue_number": issue_number,
                "p_required_specialization": required_specialization,
            },
        ).execute()

        agent_id = result.data

        if agent_id:
            activity.logger.info(f"Task #{issue_number} assigned to agent {agent_id}")
            return {
                "issue_number": issue_number,
                "agent_id": agent_id,
                "success": True,
                "reason": "Assigned successfully",
            }
        else:
            activity.logger.info(f"No available agents for task #{issue_number}")
            return {
                "issue_number": issue_number,
                "agent_id": None,
                "success": False,
                "reason": "No available agents",
            }
    except Exception as e:
        activity.logger.error(f"Failed to assign task: {e}")
        return {
            "issue_number": issue_number,
            "agent_id": None,
            "success": False,
            "reason": str(e),
        }


@activity.defn
async def register_agent(
    agent_id: str,
    hostname: str,
    specializations: Optional[List[str]] = None,
    capabilities: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Register or re-register an agent.

    Args:
        agent_id: Unique agent identifier
        hostname: Agent hostname
        specializations: List of specializations (e.g., ["temporal", "api"])
        capabilities: Additional capabilities metadata

    Returns:
        True on success
    """
    activity.logger.info(f"Registering agent {agent_id} ({hostname})")

    try:
        client = get_supabase_client()

        import json

        client.rpc(
            "register_agent",
            {
                "p_agent_id": agent_id,
                "p_hostname": hostname,
                "p_specializations": json.dumps(specializations or []),
                "p_capabilities": json.dumps(capabilities or {}),
            },
        ).execute()

        activity.logger.info(f"Agent {agent_id} registered successfully")
        return True
    except Exception as e:
        activity.logger.error(f"Failed to register agent: {e}")
        return False


@activity.defn
async def unregister_agent(agent_id: str) -> bool:
    """
    Unregister an agent (mark as offline).

    Args:
        agent_id: Agent identifier

    Returns:
        True if agent was unregistered, False if not found
    """
    activity.logger.info(f"Unregistering agent {agent_id}")

    try:
        client = get_supabase_client()

        result = client.rpc(
            "unregister_agent",
            {"p_agent_id": agent_id},
        ).execute()

        success = result.data
        if success:
            activity.logger.info(f"Agent {agent_id} unregistered")
        else:
            activity.logger.warning(
                f"Agent {agent_id} was not found or already offline"
            )

        return success
    except Exception as e:
        activity.logger.error(f"Failed to unregister agent: {e}")
        return False


@activity.defn
async def release_orphaned_agents(timeout_minutes: int = 10) -> int:
    """
    Release agents that haven't sent heartbeat for the specified duration.

    Args:
        timeout_minutes: Minutes without heartbeat before marking offline

    Returns:
        Number of agents released
    """
    activity.logger.info(f"Releasing orphaned agents (timeout={timeout_minutes}min)")

    try:
        client = get_supabase_client()

        result = client.rpc(
            "release_orphaned_agents",
            {"p_timeout_minutes": timeout_minutes},
        ).execute()

        count = result.data or 0
        if count > 0:
            activity.logger.warning(f"Released {count} orphaned agents")

        return count
    except Exception as e:
        activity.logger.error(f"Failed to release orphaned agents: {e}")
        return 0


@activity.defn
async def get_supervisor_stats() -> Dict[str, Any]:
    """
    Get current supervisor statistics.

    Returns:
        Dictionary with agent and task counts
    """
    activity.logger.info("Fetching supervisor stats")

    try:
        client = get_supabase_client()

        # Get agent counts by status
        agents_result = (
            client.schema("genomai")
            .table("agents")
            .select("status", count="exact")
            .execute()
        )

        # Get task counts by status
        tasks_result = (
            client.schema("genomai")
            .table("agent_tasks")
            .select("status", count="exact")
            .execute()
        )

        # Count by status
        agent_counts = {"online": 0, "busy": 0, "offline": 0}
        for agent in agents_result.data or []:
            status = agent.get("status", "offline")
            agent_counts[status] = agent_counts.get(status, 0) + 1

        task_counts = {"pending": 0, "claimed": 0, "completed": 0, "abandoned": 0}
        for task in tasks_result.data or []:
            status = task.get("status", "pending")
            task_counts[status] = task_counts.get(status, 0) + 1

        return {
            "agents": agent_counts,
            "tasks": task_counts,
            "total_agents": sum(agent_counts.values()),
            "total_tasks": sum(task_counts.values()),
        }
    except Exception as e:
        activity.logger.error(f"Failed to get stats: {e}")
        return {"agents": {}, "tasks": {}, "error": str(e)}
