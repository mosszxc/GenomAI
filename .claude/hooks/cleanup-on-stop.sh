#!/bin/bash
# Runs after Claude session ends - cleanup

cd "$(dirname "$0")/../.." || exit 0

# Cleanup worktrees
if [ -x "./scripts/cleanup-worktrees.sh" ]; then
    ./scripts/cleanup-worktrees.sh 2>/dev/null || true
fi

# Cleanup local dev servers
PID_DIR="/tmp/genomai-dev"
if [ -d "$PID_DIR" ]; then
    # Убить активные серверы
    for pid_file in "$PID_DIR"/*.pid; do
        [ -f "$pid_file" ] || continue
        pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            echo "Stopping dev server (PID: $pid)"
            kill "$pid" 2>/dev/null || true
        fi
        rm -f "$pid_file"
    done

    # Cleanup старых PID файлов (>15 минут) на случай zombie
    find "$PID_DIR" -name "*.pid" -mmin +15 -exec rm -f {} \; 2>/dev/null || true
fi
