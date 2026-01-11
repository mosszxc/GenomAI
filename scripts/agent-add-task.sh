#!/bin/bash
# Add a task to the Supabase agent queue
# Usage: ./scripts/agent-add-task.sh <issue-number> [title] [priority]
#
# Prerequisites:
#   - SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set
#
# Examples:
#   ./scripts/agent-add-task.sh 123 "Fix bug in login" 5
#   ./scripts/agent-add-task.sh 456  # Uses issue title from GitHub

set -e

ISSUE_NUM="$1"
TITLE="$2"
PRIORITY="${3:-0}"

if [ -z "$ISSUE_NUM" ]; then
    echo "Usage: $0 <issue-number> [title] [priority]"
    exit 1
fi

if [ -z "$SUPABASE_URL" ] || [ -z "$SUPABASE_SERVICE_ROLE_KEY" ]; then
    echo "Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set"
    exit 1
fi

# If no title provided, try to get from GitHub
if [ -z "$TITLE" ]; then
    TITLE=$(gh issue view "$ISSUE_NUM" --json title -q '.title' 2>/dev/null || echo "Issue #${ISSUE_NUM}")
fi

# Insert into agent_tasks
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
    "${SUPABASE_URL}/rest/v1/agent_tasks" \
    -H "apikey: ${SUPABASE_SERVICE_ROLE_KEY}" \
    -H "Authorization: Bearer ${SUPABASE_SERVICE_ROLE_KEY}" \
    -H "Content-Type: application/json" \
    -H "Content-Profile: genomai" \
    -H "Prefer: return=representation" \
    -d "{\"issue_number\": ${ISSUE_NUM}, \"issue_title\": \"${TITLE}\", \"priority\": ${PRIORITY}}")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "201" ] || [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Added issue #${ISSUE_NUM} to task queue (priority: ${PRIORITY})"
    echo "   Title: ${TITLE}"
else
    echo "❌ Failed to add issue #${ISSUE_NUM} to queue"
    echo "   HTTP $HTTP_CODE: $BODY"
    exit 1
fi
