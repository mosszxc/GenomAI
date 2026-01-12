#!/bin/bash
# Переключение между local и prod окружением
# Usage: source scripts/env-switch.sh [local|prod|status]
#
# ВАЖНО: Использовать с source, чтобы переменные экспортировались в текущую сессию

PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "$(dirname "$0")/..")"
ENV_TYPE="${1:-local}"

case "$ENV_TYPE" in
    local)
        if [ -f "$PROJECT_ROOT/.env.local" ]; then
            set -a
            source "$PROJECT_ROOT/.env.local"
            set +a
            echo "Switched to LOCAL environment"
            echo "  SUPABASE_URL: $SUPABASE_URL"
            echo "  PORT: $PORT"
        else
            echo "Error: .env.local not found"
            echo "Run: supabase start"
            return 1 2>/dev/null || exit 1
        fi
        ;;
    prod)
        if [ -f "$PROJECT_ROOT/.env.prod" ]; then
            set -a
            source "$PROJECT_ROOT/.env.prod"
            set +a
            echo ""
            echo "============================================"
            echo "  WARNING: PRODUCTION ENVIRONMENT ACTIVE"
            echo "============================================"
            echo ""
            echo "  SUPABASE_URL: $SUPABASE_URL"
            echo "  PORT: $PORT"
            echo ""
            echo "  Be careful with database operations!"
            echo ""
        else
            echo "Error: .env.prod not found"
            echo "Copy .env.prod.example to .env.prod and fill in values"
            return 1 2>/dev/null || exit 1
        fi
        ;;
    status)
        echo "Current environment:"
        echo "  SUPABASE_URL: ${SUPABASE_URL:-not set}"
        echo "  PORT: ${PORT:-not set}"
        if [[ "$SUPABASE_URL" == *"127.0.0.1"* ]] || [[ "$SUPABASE_URL" == *"localhost"* ]]; then
            echo "  Mode: LOCAL"
        elif [[ "$SUPABASE_URL" == *"supabase.co"* ]]; then
            echo "  Mode: PRODUCTION"
        else
            echo "  Mode: UNKNOWN"
        fi
        ;;
    *)
        echo "Usage: source $0 [local|prod|status]"
        echo ""
        echo "Options:"
        echo "  local  - Switch to local Supabase (default)"
        echo "  prod   - Switch to production Supabase (careful!)"
        echo "  status - Show current environment"
        return 1 2>/dev/null || exit 1
        ;;
esac
