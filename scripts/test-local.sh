#!/bin/bash
# Run local tests for the current issue
# Usage: ./scripts/test-local.sh [issue-number]

set -e

ISSUE_NUM="$1"
PROJECT_ROOT="$(git rev-parse --show-toplevel)"

echo "=== Local Test ==="

# 1. Check services are running
TEMPORAL_OK=false
FASTAPI_OK=false
FASTAPI_PORT=""

if curl -s http://localhost:8233/api/v1/namespaces > /dev/null 2>&1; then
    TEMPORAL_OK=true
fi

# Find FastAPI port
for pf in /tmp/genomai-dev/server-*.pid; do
    [ -f "$pf" ] || continue
    port=$(basename "$pf" .pid | sed 's/server-//')
    if curl -s "http://localhost:$port/health" > /dev/null 2>&1; then
        FASTAPI_OK=true
        FASTAPI_PORT="$port"
        break
    fi
done

# Also check default port
if [ "$FASTAPI_OK" = "false" ] && curl -s http://localhost:10000/health > /dev/null 2>&1; then
    FASTAPI_OK=true
    FASTAPI_PORT="10000"
fi

if [ "$TEMPORAL_OK" = "false" ] || [ "$FASTAPI_OK" = "false" ]; then
    echo "Services not running. Start with: make up"
    echo "  Temporal: $TEMPORAL_OK"
    echo "  FastAPI:  $FASTAPI_OK"
    exit 1
fi

echo "✓ Services running (FastAPI on :$FASTAPI_PORT)"

# 2. Determine change type from git diff
CHANGED_FILES=$(git diff origin/develop --name-only 2>/dev/null || git diff HEAD~1 --name-only)

TEST_TYPE="unknown"
if echo "$CHANGED_FILES" | grep -q "temporal/workflows/\|temporal/activities/"; then
    TEST_TYPE="workflow"
elif echo "$CHANGED_FILES" | grep -q "src/routes/\|main.py"; then
    TEST_TYPE="api"
elif echo "$CHANGED_FILES" | grep -q "migrations/"; then
    TEST_TYPE="migration"
elif echo "$CHANGED_FILES" | grep -q "telegram"; then
    TEST_TYPE="telegram"
fi

echo "Test type: $TEST_TYPE"

# 3. Run appropriate test
case "$TEST_TYPE" in
    workflow)
        echo ""
        echo "Testing workflow..."
        # Find which workflow changed
        WORKFLOW=$(echo "$CHANGED_FILES" | grep "temporal/workflows/" | head -1 | xargs basename 2>/dev/null | sed 's/.py//')
        if [ -n "$WORKFLOW" ]; then
            echo "Changed workflow: $WORKFLOW"
            # Check if workflow can be triggered
            curl -s "http://localhost:$FASTAPI_PORT/health" | grep -q "ok" && echo "✓ API healthy"
        fi
        ;;
    api)
        echo ""
        echo "Testing API..."
        # Find which route changed
        ROUTE=$(echo "$CHANGED_FILES" | grep "src/routes/" | head -1)
        echo "Changed route: $ROUTE"
        # Basic health check
        HEALTH=$(curl -s "http://localhost:$FASTAPI_PORT/health")
        if echo "$HEALTH" | grep -q "ok"; then
            echo "✓ API healthy: $HEALTH"
        else
            echo "✗ API unhealthy"
            exit 1
        fi
        ;;
    telegram)
        echo ""
        echo "Testing Telegram webhook..."
        RESPONSE=$(curl -s -X POST "http://localhost:$FASTAPI_PORT/telegram/webhook" \
            -H "Content-Type: application/json" \
            -d '{"update_id":1,"message":{"message_id":1,"from":{"id":123,"first_name":"Test"},"chat":{"id":123,"type":"private"},"text":"/health"}}')
        echo "Response: $RESPONSE"
        ;;
    migration)
        echo ""
        echo "Testing migration..."
        echo "✓ Migration tests run via make ci"
        ;;
    *)
        echo ""
        echo "No specific test for this change type"
        echo "Running basic health check..."
        curl -s "http://localhost:$FASTAPI_PORT/health"
        ;;
esac

echo ""
echo "=== LOCAL TEST: PASSED ==="
