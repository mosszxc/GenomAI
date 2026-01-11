#!/bin/bash
# Atomically claim a task from the Supabase queue
# Usage: ./scripts/agent-claim.sh <issue-number>
#
# Prerequisites:
#   - SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set
#
# Returns:
#   0 - Claim successful
#   1 - Claim failed (already claimed or not found)

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

# Call the atomic claim function via RPC
RESPONSE=$(curl -s -X POST \
    "${SUPABASE_URL}/rest/v1/rpc/claim_agent_task" \
    -H "apikey: ${SUPABASE_SERVICE_ROLE_KEY}" \
    -H "Authorization: Bearer ${SUPABASE_SERVICE_ROLE_KEY}" \
    -H "Content-Type: application/json" \
    -d "{\"p_issue_number\": ${ISSUE_NUM}, \"p_agent_id\": \"${AGENT_ID}\"}")

# Check if claim succeeded (returns true/false)
if [ "$RESPONSE" = "true" ]; then
    echo "✅ Claimed issue #${ISSUE_NUM} as agent ${AGENT_ID}"
    exit 0
else
    echo "❌ Failed to claim issue #${ISSUE_NUM} (already claimed or not in queue)"
    exit 1
fi
