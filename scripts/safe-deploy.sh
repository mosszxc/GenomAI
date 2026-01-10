#!/bin/bash
# Safe deploy: check for in-progress deploys before pushing
# Usage: ./scripts/safe-deploy.sh [--force]
#
# Requires: RENDER_API_KEY environment variable
# Service ID: srv-ctpat9ij1k6c73a6r530 (genomai)

set -e

SERVICE_ID="srv-d54vf524d50c739kc2m0"
MAX_WAIT_SECONDS=600  # 10 minutes max wait
POLL_INTERVAL=30      # Check every 30 seconds

FORCE=""
if [ "$1" = "--force" ]; then
    FORCE="true"
    echo "⚠️  Force mode: skipping deploy check"
fi

# Check for API key
if [ -z "$RENDER_API_KEY" ]; then
    echo "Error: RENDER_API_KEY not set"
    echo ""
    echo "Options:"
    echo "  1. Export RENDER_API_KEY"
    echo "  2. Use --force to skip check (risky with parallel agents)"
    exit 1
fi

check_deploy_status() {
    # Get latest deploy
    RESPONSE=$(curl -s -H "Authorization: Bearer $RENDER_API_KEY" \
        "https://api.render.com/v1/services/$SERVICE_ID/deploys?limit=1")

    STATUS=$(echo "$RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d[0]['deploy']['status'] if d else 'none')" 2>/dev/null || echo "error")
    echo "$STATUS"
}

wait_for_deploy() {
    local elapsed=0

    while [ $elapsed -lt $MAX_WAIT_SECONDS ]; do
        STATUS=$(check_deploy_status)

        case "$STATUS" in
            "live"|"deactivated"|"canceled"|"none")
                echo "✓ No active deploy. Ready to push."
                return 0
                ;;
            "build_in_progress"|"update_in_progress"|"pre_deploy_in_progress")
                echo "⏳ Deploy in progress ($STATUS). Waiting ${POLL_INTERVAL}s... (${elapsed}s elapsed)"
                sleep $POLL_INTERVAL
                elapsed=$((elapsed + POLL_INTERVAL))
                ;;
            "error")
                echo "⚠️  Could not check deploy status. Proceeding anyway."
                return 0
                ;;
            *)
                echo "Status: $STATUS. Proceeding."
                return 0
                ;;
        esac
    done

    echo "❌ Timeout waiting for deploy to complete"
    exit 1
}

# Main flow
if [ "$FORCE" != "true" ]; then
    echo "=== Safe Deploy ==="
    echo "Checking for active deploys..."
    wait_for_deploy
fi

# Push to origin
echo ""
echo "Pushing to origin..."
git push

echo ""
echo "Push complete. Waiting 180s for deploy..."
sleep 180

echo ""
echo "=== Deploy should be complete ==="
echo "Verify at: https://dashboard.render.com/web/$SERVICE_ID"
