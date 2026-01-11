#!/bin/bash
# Get and claim the next task from the Supabase queue
# Usage: ./scripts/agent-next.sh
#
# Prerequisites:
#   - SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set
#   - ~/.claude-agent-id must exist (run /ag1-/ag5 first)
#
# Returns:
#   Issue number on success (to stdout)
#   Exit code 0 on success, 1 on failure or empty queue

set -e

# Read agent ID from file
if [ -f ~/.claude-agent-id ]; then
    AGENT_ID=$(cat ~/.claude-agent-id)
else
    echo "Error: Run /ag1, /ag2, /ag3, /ag4 or /ag5 first to set agent identity" >&2
    exit 1
fi

if [ -z "$SUPABASE_URL" ] || [ -z "$SUPABASE_SERVICE_ROLE_KEY" ]; then
    echo "Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set" >&2
    exit 1
fi

# Get next pending task
TASK=$(curl -s -X GET \
    "${SUPABASE_URL}/rest/v1/agent_tasks?status=eq.pending&order=priority.desc,created_at.asc&limit=1" \
    -H "apikey: ${SUPABASE_SERVICE_ROLE_KEY}" \
    -H "Authorization: Bearer ${SUPABASE_SERVICE_ROLE_KEY}" \
    -H "Accept-Profile: genomai")

# Check if we got a task
ISSUE_NUM=$(echo "$TASK" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d[0]['issue_number'] if d else '')" 2>/dev/null || echo "")

if [ -z "$ISSUE_NUM" ]; then
    echo "No tasks in queue" >&2
    exit 1
fi

# Try to claim the task
CLAIM_RESULT=$(curl -s -X POST \
    "${SUPABASE_URL}/rest/v1/rpc/claim_agent_task" \
    -H "apikey: ${SUPABASE_SERVICE_ROLE_KEY}" \
    -H "Authorization: Bearer ${SUPABASE_SERVICE_ROLE_KEY}" \
    -H "Content-Type: application/json" \
    -d "{\"p_issue_number\": ${ISSUE_NUM}, \"p_agent_id\": \"${AGENT_ID}\"}")

if [ "$CLAIM_RESULT" = "true" ]; then
    echo "$ISSUE_NUM"
    exit 0
else
    echo "Failed to claim issue #${ISSUE_NUM} (may have been claimed by another agent)" >&2
    exit 1
fi
