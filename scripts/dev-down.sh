#!/bin/bash
# Stop all local development services
# Usage: ./scripts/dev-down.sh

PID_DIR="/tmp/genomai-dev"

echo "=== Stopping GenomAI local environment ==="

stopped=0

# Stop FastAPI
for pf in "$PID_DIR"/server-*.pid; do
    [ -f "$pf" ] || continue
    pid=$(cat "$pf")
    if kill "$pid" 2>/dev/null; then
        echo "✓ FastAPI stopped (PID: $pid)"
        ((stopped++))
    fi
    rm -f "$pf"
done

# Stop Worker
if [ -f "$PID_DIR/worker.pid" ]; then
    pid=$(cat "$PID_DIR/worker.pid")
    if kill "$pid" 2>/dev/null; then
        echo "✓ Worker stopped (PID: $pid)"
        ((stopped++))
    fi
    rm -f "$PID_DIR/worker.pid"
fi

# Stop Temporal
if [ -f "$PID_DIR/temporal.pid" ]; then
    pid=$(cat "$PID_DIR/temporal.pid")
    if kill "$pid" 2>/dev/null; then
        echo "✓ Temporal stopped (PID: $pid)"
        ((stopped++))
    fi
    rm -f "$PID_DIR/temporal.pid"
fi

# Cleanup logs
rm -f "$PID_DIR"/*.log 2>/dev/null

if [ $stopped -eq 0 ]; then
    echo "Nothing was running."
else
    echo ""
    echo "=== All services stopped ==="
fi
