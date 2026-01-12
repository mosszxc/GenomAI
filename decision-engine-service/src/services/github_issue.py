"""
GitHub Issue Creation Service

Creates issues in GenomAI repository via GitHub REST API.
Used for buyer feedback from Telegram.
"""

import os
import logging
from datetime import datetime
from typing import Optional
from dataclasses import dataclass

import httpx
from src.core.http_client import get_http_client

logger = logging.getLogger(__name__)

GITHUB_REPO = "mosszxc/GenomAI"
GITHUB_API_URL = "https://api.github.com"


@dataclass
class IssueResult:
    """Result of issue creation."""

    success: bool
    issue_number: Optional[int] = None
    issue_url: Optional[str] = None
    error: Optional[str] = None


async def create_feedback_issue(
    text: str,
    telegram_id: str,
    buyer_name: Optional[str] = None,
) -> IssueResult:
    """
    Create a GitHub issue from buyer feedback.

    Args:
        text: Feedback text from buyer
        telegram_id: Buyer's Telegram ID
        buyer_name: Optional buyer name

    Returns:
        IssueResult with success status and issue number
    """
    github_token = os.getenv("GITHUB_TOKEN")

    if not github_token:
        logger.error("GITHUB_TOKEN not configured")
        return IssueResult(success=False, error="GitHub integration not configured")

    # Generate title from first 50 chars of text
    title_text = text[:50].strip()
    if len(text) > 50:
        title_text += "..."
    title = f"[FEEDBACK] {title_text}"

    # Format body with metadata
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    buyer_info = f"`{telegram_id}`"
    if buyer_name:
        buyer_info += f" ({buyer_name})"

    body = f"""{text}

---
**Submitted via Telegram**
- Buyer: {buyer_info}
- Time: {timestamp}
"""

    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    payload = {
        "title": title,
        "body": body,
        "labels": ["buyer-feedback"],
    }

    try:
        client = get_http_client()
        response = await client.post(
            f"{GITHUB_API_URL}/repos/{GITHUB_REPO}/issues",
            headers=headers,
            json=payload,
            timeout=30.0,
        )

        if response.status_code == 201:
            data = response.json()
            logger.info(f"Created feedback issue #{data['number']}: {title}")
            return IssueResult(
                success=True,
                issue_number=data["number"],
                issue_url=data["html_url"],
            )
        else:
            error_msg = response.json().get("message", "Unknown error")
            logger.error(f"GitHub API error: {response.status_code} - {error_msg}")
            return IssueResult(success=False, error=error_msg)

    except httpx.TimeoutException:
        logger.error("GitHub API timeout")
        return IssueResult(success=False, error="Request timeout")
    except Exception as e:
        logger.error(f"Failed to create GitHub issue: {e}")
        return IssueResult(success=False, error=str(e))
