#!/bin/bash
# Запускает локальный сервер с трекингом PID для cleanup

set -e

PID_DIR="/tmp/genomai-dev"
mkdir -p "$PID_DIR"

# Lock для предотвращения race condition при параллельном старте (macOS compatible)
LOCK_DIR="$PID_DIR/.lock"
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
    echo "Another server starting, waiting..."
    sleep 1
    exec "$0" "$@"
fi

# Cleanup старых PID файлов (>15 минут)
find "$PID_DIR" -name "*.pid" -mmin +15 -exec rm -f {} \; 2>/dev/null || true

# Найти свободный порт
PORT=${PORT:-$(python3 -c "import socket; s=socket.socket(); s.bind(('',0)); print(s.getsockname()[1]); s.close()")}

PID_FILE="$PID_DIR/server-$PORT.pid"

# Освободить lock после получения порта (другие могут стартовать)
rmdir "$LOCK_DIR" 2>/dev/null || true

# Cleanup при выходе (сервер + PID файл)
cleanup() {
    if [ -f "$PID_FILE" ]; then
        kill $(cat "$PID_FILE") 2>/dev/null || true
        rm -f "$PID_FILE"
    fi
}
trap cleanup EXIT

cd "$(dirname "$0")/../decision-engine-service"

# Определить Python 3.10+
if command -v python3.12 &>/dev/null; then
    PYTHON_BIN="python3.12"
elif command -v python3.11 &>/dev/null; then
    PYTHON_BIN="python3.11"
elif command -v python3.10 &>/dev/null; then
    PYTHON_BIN="python3.10"
else
    PYTHON_BIN="python3"
fi

# Создать venv если не существует
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment with $PYTHON_BIN..."
    $PYTHON_BIN -m venv .venv
    .venv/bin/pip install -q -r requirements.txt
fi

# Активировать venv
source .venv/bin/activate

echo "Starting server on port $PORT"
echo "PID file: $PID_FILE"

# Запуск сервера
.venv/bin/uvicorn main:app --reload --reload-dir src --host 0.0.0.0 --port $PORT &
SERVER_PID=$!
echo $SERVER_PID > "$PID_FILE"

# Health check - ждём пока сервер поднимется
echo "Waiting for server to be ready..."
for i in {1..30}; do
    if curl -s "http://localhost:$PORT/health" > /dev/null 2>&1; then
        echo "Server ready on http://localhost:$PORT"
        break
    fi
    sleep 1
done

# Ждём сервер
wait $SERVER_PID
