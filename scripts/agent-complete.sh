#!/bin/bash
# Mark a claimed task as completed
# Usage: ./scripts/agent-complete.sh <issue-number>
#
# Prerequisites:
#   - SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set
#   - Task must be currently claimed by this agent
#
# Returns:
#   0 - Completion successful
#   1 - Completion failed (not claimed by this agent)

set -e

ISSUE_NUM="$1"
AGENT_ID="${HOSTNAME:-$(hostname)}-$$"

if [ -z "$ISSUE_NUM" ]; then
    echo "Usage: $0 <issue-number>"
    exit 1
fi

if [ -z "$SUPABASE_URL" ] || [ -z "$SUPABASE_SERVICE_ROLE_KEY" ]; then
    echo "Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set"
    exit 1
fi

# Call the complete function via RPC
RESPONSE=$(curl -s -X POST \
    "${SUPABASE_URL}/rest/v1/rpc/complete_agent_task" \
    -H "apikey: ${SUPABASE_SERVICE_ROLE_KEY}" \
    -H "Authorization: Bearer ${SUPABASE_SERVICE_ROLE_KEY}" \
    -H "Content-Type: application/json" \
    -d "{\"p_issue_number\": ${ISSUE_NUM}, \"p_agent_id\": \"${AGENT_ID}\"}")

if [ "$RESPONSE" = "true" ]; then
    echo "✅ Completed issue #${ISSUE_NUM}"
    exit 0
else
    echo "❌ Failed to complete issue #${ISSUE_NUM} (not claimed by this agent)"
    exit 1
fi
