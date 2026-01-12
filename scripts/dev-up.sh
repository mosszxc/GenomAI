#!/bin/bash
# Start all local development services
# Usage: ./scripts/dev-up.sh

set -e

PROJECT_ROOT="$(git rev-parse --show-toplevel)"
PID_DIR="/tmp/genomai-dev"
mkdir -p "$PID_DIR"

echo "=== Starting GenomAI local environment ==="

# Check if already running
if [ -f "$PID_DIR/temporal.pid" ] && kill -0 "$(cat "$PID_DIR/temporal.pid")" 2>/dev/null; then
    echo "Already running. Use ./scripts/dev-down.sh to stop first."
    exit 1
fi

# 1. Start Temporal server
echo ""
echo "[1/3] Starting Temporal server..."
temporal server start-dev --log-level error > "$PID_DIR/temporal.log" 2>&1 &
echo $! > "$PID_DIR/temporal.pid"
sleep 3

if kill -0 "$(cat "$PID_DIR/temporal.pid")" 2>/dev/null; then
    echo "      ✓ Temporal running (http://localhost:8233)"
else
    echo "      ✗ Temporal failed to start"
    cat "$PID_DIR/temporal.log"
    exit 1
fi

# 2. Start Temporal worker
echo ""
echo "[2/3] Starting Temporal worker..."
cd "$PROJECT_ROOT/decision-engine-service"
python3 -m temporal.worker > "$PID_DIR/worker.log" 2>&1 &
echo $! > "$PID_DIR/worker.pid"
cd "$PROJECT_ROOT"
sleep 2

if kill -0 "$(cat "$PID_DIR/worker.pid")" 2>/dev/null; then
    echo "      ✓ Worker running"
else
    echo "      ✗ Worker failed to start"
    cat "$PID_DIR/worker.log"
    exit 1
fi

# 3. Start FastAPI
echo ""
echo "[3/3] Starting FastAPI server..."
"$PROJECT_ROOT/scripts/local-dev.sh" > "$PID_DIR/fastapi.log" 2>&1 &
sleep 5

# Find FastAPI port
FASTAPI_PORT=""
for pf in "$PID_DIR"/server-*.pid; do
    [ -f "$pf" ] || continue
    FASTAPI_PORT=$(basename "$pf" .pid | sed 's/server-//')
    break
done

if [ -n "$FASTAPI_PORT" ]; then
    echo "      ✓ FastAPI running (http://localhost:$FASTAPI_PORT)"
else
    echo "      ✗ FastAPI failed to start"
    cat "$PID_DIR/fastapi.log"
    exit 1
fi

echo ""
echo "=== All services running ==="
echo ""
echo "  Temporal UI:  http://localhost:8233"
echo "  FastAPI:      http://localhost:$FASTAPI_PORT"
echo ""
echo "Logs: $PID_DIR/*.log"
echo ""
echo "To stop: ./scripts/dev-down.sh"
