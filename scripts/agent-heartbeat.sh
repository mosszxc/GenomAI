#!/bin/bash
# Send heartbeat for a claimed task
# Usage: ./scripts/agent-heartbeat.sh <issue-number>
#
# This should be called periodically (every 2-5 minutes) while working on a task.
# Tasks without heartbeat for 10+ minutes will be considered abandoned.
#
# Prerequisites:
#   - SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set
#
# Returns:
#   0 - Heartbeat successful (task still owned)
#   1 - Heartbeat failed (task was released or claimed by another agent)

set -e

ISSUE_NUM="$1"

# Read agent ID from file if exists, otherwise generate from hostname and PID
if [ -f ~/.claude-agent-id ]; then
    AGENT_ID=$(cat ~/.claude-agent-id)
else
    AGENT_ID="${HOSTNAME:-$(hostname)}-$$"
fi

if [ -z "$ISSUE_NUM" ]; then
    echo "Usage: $0 <issue-number>"
    exit 1
fi

if [ -z "$SUPABASE_URL" ] || [ -z "$SUPABASE_SERVICE_ROLE_KEY" ]; then
    echo "Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set"
    exit 1
fi

# Call the heartbeat function via RPC
RESPONSE=$(curl -s -X POST \
    "${SUPABASE_URL}/rest/v1/rpc/heartbeat_agent_task" \
    -H "apikey: ${SUPABASE_SERVICE_ROLE_KEY}" \
    -H "Authorization: Bearer ${SUPABASE_SERVICE_ROLE_KEY}" \
    -H "Content-Type: application/json" \
    -d "{\"p_issue_number\": ${ISSUE_NUM}, \"p_agent_id\": \"${AGENT_ID}\"}")

if [ "$RESPONSE" = "true" ]; then
    echo "💓 Heartbeat sent for issue #${ISSUE_NUM}"
    exit 0
else
    echo "⚠️ Heartbeat failed for issue #${ISSUE_NUM} - task may have been released"
    exit 1
fi
