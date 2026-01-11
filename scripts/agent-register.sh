#!/bin/bash
# Register an agent with the Supabase agent registry
# Usage: ./scripts/agent-register.sh [specializations]
#
# Prerequisites:
#   - SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set
#
# Examples:
#   ./scripts/agent-register.sh                          # No specializations
#   ./scripts/agent-register.sh temporal migration       # With specializations
#   ./scripts/agent-register.sh "temporal,api,telegram"  # Comma-separated

set -e

# Read agent ID from file if exists, otherwise generate from hostname and PID
if [ -f ~/.claude-agent-id ]; then
    AGENT_ID=$(cat ~/.claude-agent-id)
else
    AGENT_ID="${HOSTNAME:-$(hostname)}-$$"
    echo "⚠️  Tip: Run /ag1-/ag5 to set a persistent agent identity"
fi
HOSTNAME_VAL="${HOSTNAME:-$(hostname)}"

if [ -z "$SUPABASE_URL" ] || [ -z "$SUPABASE_SERVICE_ROLE_KEY" ]; then
    echo "Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set"
    exit 1
fi

# Parse specializations from arguments
SPECIALIZATIONS="[]"
if [ $# -gt 0 ]; then
    # Handle both "spec1 spec2" and "spec1,spec2" formats
    SPECS=""
    for arg in "$@"; do
        # Split by comma if present
        IFS=',' read -ra PARTS <<< "$arg"
        for part in "${PARTS[@]}"; do
            part=$(echo "$part" | xargs)  # Trim whitespace
            if [ -n "$part" ]; then
                if [ -n "$SPECS" ]; then
                    SPECS="$SPECS,\"$part\""
                else
                    SPECS="\"$part\""
                fi
            fi
        done
    done
    SPECIALIZATIONS="[$SPECS]"
fi

# Call the register_agent RPC function
RESPONSE=$(curl -s -X POST \
    "${SUPABASE_URL}/rest/v1/rpc/register_agent" \
    -H "apikey: ${SUPABASE_SERVICE_ROLE_KEY}" \
    -H "Authorization: Bearer ${SUPABASE_SERVICE_ROLE_KEY}" \
    -H "Content-Type: application/json" \
    -d "{
        \"p_agent_id\": \"${AGENT_ID}\",
        \"p_hostname\": \"${HOSTNAME_VAL}\",
        \"p_specializations\": ${SPECIALIZATIONS},
        \"p_capabilities\": {}
    }")

# Check response
if [ "$RESPONSE" = "true" ]; then
    echo "✅ Agent registered successfully"
    echo "   Agent ID: ${AGENT_ID}"
    echo "   Hostname: ${HOSTNAME_VAL}"
    echo "   Specializations: ${SPECIALIZATIONS}"
    echo ""
    echo "To send heartbeats, run periodically:"
    echo "   ./scripts/agent-heartbeat.sh"
    echo ""
    echo "To unregister when done:"
    echo "   ./scripts/agent-unregister.sh"
    exit 0
else
    echo "❌ Failed to register agent"
    echo "   Response: $RESPONSE"
    exit 1
fi
