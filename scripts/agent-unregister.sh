#!/bin/bash
# Unregister an agent from the Supabase agent registry
# Usage: ./scripts/agent-unregister.sh [agent-id]
#
# Prerequisites:
#   - SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set
#
# If no agent-id is provided, uses the current hostname-PID pattern.

set -e

# Get agent ID (from argument or generate from hostname)
if [ -n "$1" ]; then
    AGENT_ID="$1"
else
    AGENT_ID="${HOSTNAME:-$(hostname)}-$$"
fi

if [ -z "$SUPABASE_URL" ] || [ -z "$SUPABASE_SERVICE_ROLE_KEY" ]; then
    echo "Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set"
    exit 1
fi

# Call the unregister_agent RPC function
RESPONSE=$(curl -s -X POST \
    "${SUPABASE_URL}/rest/v1/rpc/unregister_agent" \
    -H "apikey: ${SUPABASE_SERVICE_ROLE_KEY}" \
    -H "Authorization: Bearer ${SUPABASE_SERVICE_ROLE_KEY}" \
    -H "Content-Type: application/json" \
    -d "{\"p_agent_id\": \"${AGENT_ID}\"}")

# Check response
if [ "$RESPONSE" = "true" ]; then
    echo "✅ Agent ${AGENT_ID} unregistered (marked offline)"
    exit 0
elif [ "$RESPONSE" = "false" ]; then
    echo "⚠️  Agent ${AGENT_ID} was not found or already offline"
    exit 0
else
    echo "❌ Failed to unregister agent"
    echo "   Response: $RESPONSE"
    exit 1
fi
