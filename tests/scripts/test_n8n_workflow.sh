#!/bin/bash

# GenomAI — n8n Workflow Test Script (Bash)
# Версия: v1.0
# Назначение: Автоматизированное тестирование n8n workflows с Manual Trigger
# 
# Решает проблему: не нужно постоянно нажимать на Manual Trigger и проверять execution вручную

set -e

# Цвета
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# Конфигурация
N8N_API_URL="${N8N_API_URL:-https://kazamaqwe.app.n8n.cloud/api/v1}"
N8N_API_KEY="${N8N_API_KEY:-}"
WORKFLOW_ID="${WORKFLOW_ID:-$1}"
TIMEOUT="${TIMEOUT:-120000}"
POLL_INTERVAL="${POLL_INTERVAL:-1000}"
VERBOSE="${VERBOSE:-false}"
WAIT_FOR_MANUAL="${WAIT_FOR_MANUAL:-true}"

# Функции логирования
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_debug() {
    if [ "$VERBOSE" = "true" ]; then
        echo -e "${CYAN}[DEBUG]${NC} $1"
    fi
}

log_header() {
    echo -e "${MAGENTA}[HEADER]${NC} $1"
}

# Проверка зависимостей
check_dependencies() {
    if ! command -v curl &> /dev/null; then
        log_error "curl не установлен!"
        exit 1
    fi
    
    if ! command -v jq &> /dev/null; then
        log_warning "jq не установлен. JSON парсинг будет ограничен."
        log_info "Установите jq для лучшей работы: brew install jq (macOS) или apt-get install jq (Linux)"
    fi
}

# HTTP request helper
make_request() {
    local method="${1:-GET}"
    local url="$2"
    local body="${3:-}"
    
    local curl_opts=(
        -s
        -w "\n%{http_code}"
        -X "$method"
        -H "Content-Type: application/json"
        -H "X-N8N-API-KEY: $N8N_API_KEY"
    )
    
    if [ -n "$body" ]; then
        curl_opts+=(-d "$body")
    fi
    
    curl "${curl_opts[@]}" "$url" 2>&1
}

# Получить информацию о workflow
get_workflow() {
    log_info "Получение информации о workflow: $WORKFLOW_ID"
    
    local response=$(make_request "GET" "${N8N_API_URL}/workflows/${WORKFLOW_ID}")
    local http_code=$(echo "$response" | tail -n1)
    local body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ]; then
        if command -v jq &> /dev/null; then
            local name=$(echo "$body" | jq -r '.name // "unknown"')
            local active=$(echo "$body" | jq -r '.active // false')
            log_success "Workflow найден: $name"
            log_debug "Active: $active"
        else
            log_success "Workflow найден"
        fi
        echo "$body"
    else
        log_error "Ошибка при получении workflow: HTTP $http_code"
        echo "$body" >&2
        return 1
    fi
}

# Получить последний execution
get_last_execution() {
    local response=$(make_request "GET" "${N8N_API_URL}/executions?workflowId=${WORKFLOW_ID}&limit=1")
    local http_code=$(echo "$response" | tail -n1)
    local body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ]; then
        if command -v jq &> /dev/null; then
            local execution=$(echo "$body" | jq -r '.data[0] // empty')
            if [ -n "$execution" ] && [ "$execution" != "null" ]; then
                echo "$execution"
            fi
        else
            echo "$body"
        fi
    fi
}

# Получить детали execution
get_execution_details() {
    local execution_id="$1"
    local response=$(make_request "GET" "${N8N_API_URL}/executions/${execution_id}")
    local http_code=$(echo "$response" | tail -n1)
    local body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ]; then
        echo "$body"
    fi
}

# Проверить статус execution
check_execution_status() {
    local execution_json="$1"
    
    if ! command -v jq &> /dev/null; then
        log_warning "jq не установлен. Детальная проверка недоступна."
        echo "$execution_json"
        return
    fi
    
    echo "============================================================"
    log_header "Execution Status"
    echo "============================================================"
    
    local id=$(echo "$execution_json" | jq -r '.id // "unknown"')
    local finished=$(echo "$execution_json" | jq -r '.finished // false')
    local mode=$(echo "$execution_json" | jq -r '.mode // "unknown"')
    local started_at=$(echo "$execution_json" | jq -r '.startedAt // "unknown"')
    local stopped_at=$(echo "$execution_json" | jq -r '.stoppedAt // "unknown"')
    
    log_info "Execution ID: $id"
    log_info "Status: $([ "$finished" = "true" ] && echo "finished" || echo "running")"
    log_info "Mode: $mode"
    
    if [ "$started_at" != "null" ] && [ "$started_at" != "unknown" ]; then
        log_info "Started: $started_at"
    fi
    
    if [ "$stopped_at" != "null" ] && [ "$stopped_at" != "unknown" ]; then
        log_info "Stopped: $stopped_at"
        
        if [ "$started_at" != "null" ] && [ "$started_at" != "unknown" ]; then
            # Простой расчёт duration (требует date команды)
            log_info "Duration: calculated"
        fi
    fi
    
    # Проверка ошибок
    local has_error=$(echo "$execution_json" | jq -r '.data.resultData.error // empty')
    if [ -n "$has_error" ] && [ "$has_error" != "null" ]; then
        log_error "Execution завершился с ошибкой!"
        if [ "$VERBOSE" = "true" ]; then
            log_debug "Error: $(echo "$execution_json" | jq -r '.data.resultData.error')"
        fi
        return 1
    elif [ "$finished" = "true" ]; then
        log_success "Execution завершился успешно!"
        
        # Статистика по нодам
        local nodes=$(echo "$execution_json" | jq -r '.data.resultData.runData | keys | length // 0')
        if [ "$nodes" -gt 0 ]; then
            log_info "Выполнено нод: $nodes"
        fi
        
        return 0
    else
        log_warning "Execution ещё выполняется..."
        return 2
    fi
}

# Ждать новый execution
wait_for_execution() {
    local previous_id="${1:-}"
    local start_time=$(date +%s)
    local timeout_seconds=$((TIMEOUT / 1000))
    local last_id="$previous_id"
    
    log_info "Ожидание нового execution (timeout: ${timeout_seconds}s)..."
    
    while true; do
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))
        
        if [ $elapsed -ge $timeout_seconds ]; then
            log_error "Timeout: новый execution не появился"
            return 1
        fi
        
        sleep $((POLL_INTERVAL / 1000))
        
        local execution=$(get_last_execution)
        if [ -n "$execution" ]; then
            if command -v jq &> /dev/null; then
                local current_id=$(echo "$execution" | jq -r '.id // empty')
                if [ -n "$current_id" ] && [ "$current_id" != "$last_id" ] && [ "$current_id" != "null" ]; then
                    log_success "Новый execution найден: $current_id"
                    echo "$execution"
                    return 0
                fi
            else
                # Без jq просто возвращаем последний execution
                echo "$execution"
                return 0
            fi
        fi
    done
}

# Основная функция
main() {
    echo "============================================================"
    log_header "GenomAI — n8n Workflow Test Script"
    echo "============================================================"
    log_info "Workflow ID: $WORKFLOW_ID"
    log_info "API URL: $N8N_API_URL"
    log_info "Timeout: ${TIMEOUT}ms"
    echo ""
    
    if [ -z "$N8N_API_KEY" ]; then
        log_error "N8N_API_KEY не установлен!"
        log_info "Установите переменную окружения: export N8N_API_KEY=\"your-api-key\""
        exit 1
    fi
    
    if [ -z "$WORKFLOW_ID" ]; then
        echo "Использование:"
        echo "  $0 <workflow-id>"
        echo ""
        echo "Или установите переменные окружения:"
        echo "  export WORKFLOW_ID=\"your-workflow-id\""
        echo "  export N8N_API_KEY=\"your-api-key\""
        echo "  export N8N_API_URL=\"https://your-n8n-instance.com/api/v1\""
        echo ""
        echo "Опции:"
        echo "  VERBOSE=true - подробный вывод"
        echo "  TIMEOUT=120000 - timeout в миллисекундах"
        echo "  POLL_INTERVAL=1000 - интервал проверки в миллисекундах"
        echo "  WAIT_FOR_MANUAL=true - ждать ручного запуска"
        exit 1
    fi
    
    check_dependencies
    echo ""
    
    # Получить workflow
    local workflow=$(get_workflow)
    echo ""
    
    # Получить последний execution до запуска
    log_info "Получение последнего execution до запуска..."
    local previous_execution=$(get_last_execution)
    local previous_id=""
    
    if [ -n "$previous_execution" ] && command -v jq &> /dev/null; then
        previous_id=$(echo "$previous_execution" | jq -r '.id // empty')
        if [ -n "$previous_id" ] && [ "$previous_id" != "null" ]; then
            local finished=$(echo "$previous_execution" | jq -r '.finished // false')
            log_info "Последний execution до запуска: $previous_id ($([ "$finished" = "true" ] && echo "finished" || echo "running"))"
        fi
    elif [ -n "$previous_execution" ]; then
        log_info "Последний execution найден (детали требуют jq)"
    else
        log_info "Нет предыдущих executions"
    fi
    echo ""
    
    # Ждать ручного запуска
    if [ "$WAIT_FOR_MANUAL" = "true" ]; then
        log_warning "Ожидание ручного запуска через Manual Trigger..."
        log_info "Запустите workflow вручную в n8n UI, скрипт будет ждать новый execution..."
        echo ""
        
        local new_execution=$(wait_for_execution "$previous_id")
        if [ -n "$new_execution" ]; then
            local execution_id=""
            if command -v jq &> /dev/null; then
                execution_id=$(echo "$new_execution" | jq -r '.id // empty')
            fi
            
            if [ -n "$execution_id" ] && [ "$execution_id" != "null" ]; then
                local details=$(get_execution_details "$execution_id")
                echo ""
                check_execution_status "$details"
                echo ""
                
                # Exit code based on status
                if echo "$details" | jq -e '.data.resultData.error' > /dev/null 2>&1; then
                    exit 1
                elif echo "$details" | jq -e '.finished == true' > /dev/null 2>&1; then
                    exit 0
                else
                    exit 2
                fi
            fi
        else
            log_error "Не удалось получить новый execution"
            exit 1
        fi
    else
        log_warning "WAIT_FOR_MANUAL=false. Используйте Manual Trigger вручную."
        log_info "Для автоматического ожидания установите: WAIT_FOR_MANUAL=true"
        exit 0
    fi
}

main "$@"


