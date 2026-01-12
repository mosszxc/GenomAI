#!/bin/bash
# Запуск полного локального окружения: Supabase + FastAPI
# Usage: ./scripts/local-full.sh [--reset] [--no-server]
#
# Options:
#   --reset     Reset database (apply all migrations from scratch)
#   --no-server Only start Supabase, don't start FastAPI server

set -e

PROJECT_ROOT="$(git rev-parse --show-toplevel)"

RESET_DB=""
NO_SERVER=""

for arg in "$@"; do
    case $arg in
        --reset)
            RESET_DB="true"
            ;;
        --no-server)
            NO_SERVER="true"
            ;;
    esac
done

echo "=== GenomAI Local Environment ==="
echo ""

# 1. Проверить Docker
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running!"
    echo "Please start Docker Desktop and try again."
    exit 1
fi

# 2. Запуск Supabase
cd "$PROJECT_ROOT"

if [ "$RESET_DB" == "true" ]; then
    echo "Step 1: Resetting database (applying all migrations)..."
    supabase db reset
else
    echo "Step 1: Starting Supabase..."
    # Проверить не запущен ли уже
    if curl -s "http://127.0.0.1:54321/rest/v1/" > /dev/null 2>&1; then
        echo "  Supabase already running"
    else
        supabase start
    fi
fi

echo ""
echo "Step 2: Loading environment..."
source "$PROJECT_ROOT/scripts/env-switch.sh" local

# Показать статус
echo ""
supabase status

if [ "$NO_SERVER" == "true" ]; then
    echo ""
    echo "=== Supabase Ready (FastAPI skipped) ==="
    echo ""
    echo "Services:"
    echo "  Supabase Studio: http://localhost:54323"
    echo "  Supabase API:    http://localhost:54321"
    echo "  Database:        postgresql://postgres:postgres@localhost:54322/postgres"
    echo ""
    echo "To start FastAPI: ./scripts/local-dev.sh"
    echo "To stop: supabase stop"
    exit 0
fi

echo ""
echo "Step 3: Starting FastAPI server..."
echo ""

# Запуск FastAPI (не в фоне, чтобы видеть логи)
"$PROJECT_ROOT/scripts/local-dev.sh"
