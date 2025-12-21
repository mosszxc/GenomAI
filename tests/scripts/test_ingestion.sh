#!/bin/bash

# GenomAI — Ingestion Test Script
# Версия: v1.0
# Назначение: Автоматизированное тестирование STEP 01 — Ingestion

set -e  # Exit on error

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Конфигурация
WEBHOOK_URL="${WEBHOOK_URL:-http://localhost:5678/webhook/ingest/creative}"
PAYLOADS_DIR="$(dirname "$0")/../payloads/ingestion"
VERBOSE="${VERBOSE:-false}"

# Счетчики
PASSED=0
FAILED=0
TOTAL=0

# Функции
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((PASSED++))
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((FAILED++))
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

test_request() {
    local test_name="$1"
    local payload_file="$2"
    local expected_status="$3"
    local expected_behavior="$4"
    
    ((TOTAL++))
    
    log_info "Testing: $test_name"
    
    if [ ! -f "$payload_file" ]; then
        log_error "Payload file not found: $payload_file"
        return 1
    fi
    
    if [ "$VERBOSE" = "true" ]; then
        log_info "Payload: $(cat "$payload_file")"
    fi
    
    # Выполняем запрос
    response=$(curl -s -w "\n%{http_code}" -X POST "$WEBHOOK_URL" \
        -H "Content-Type: application/json" \
        -d @"$payload_file" 2>&1)
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$VERBOSE" = "true" ]; then
        log_info "HTTP Code: $http_code"
        log_info "Response: $body"
    fi
    
    # Проверяем статус код
    if [ "$http_code" = "$expected_status" ]; then
        log_success "$test_name — HTTP $http_code (expected $expected_status)"
        return 0
    else
        log_error "$test_name — HTTP $http_code (expected $expected_status)"
        return 1
    fi
}

# Заголовок
echo "=========================================="
echo "GenomAI — Ingestion Test Suite"
echo "=========================================="
echo "Webhook URL: $WEBHOOK_URL"
echo "Payloads Dir: $PAYLOADS_DIR"
echo ""

# Проверка наличия webhook URL
if [ -z "$WEBHOOK_URL" ] || [ "$WEBHOOK_URL" = "http://localhost:5678/webhook/ingest/creative" ]; then
    log_warning "WEBHOOK_URL not set. Using default: $WEBHOOK_URL"
    log_warning "Set WEBHOOK_URL environment variable to test against your n8n instance"
    echo ""
fi

# Тест 1: Happy Path
test_request \
    "Happy Path" \
    "$PAYLOADS_DIR/happy_path.json" \
    "200" \
    "Creative should be created"

# Тест 2: Idempotency (тот же payload)
log_info "Waiting 1 second before idempotency test..."
sleep 1
test_request \
    "Idempotency" \
    "$PAYLOADS_DIR/idempotency.json" \
    "200" \
    "Duplicate should not be created"

# Тест 3: Edge Case — один video_url, разные tracker_id
test_request \
    "Edge Case: Same video, different tracker (1)" \
    "$PAYLOADS_DIR/edge_same_video_different_tracker_1.json" \
    "200" \
    "Should create different creative"

test_request \
    "Edge Case: Same video, different tracker (2)" \
    "$PAYLOADS_DIR/edge_same_video_different_tracker_2.json" \
    "200" \
    "Should create different creative"

# Тест 4: Edge Case — разные video_url, один tracker_id
test_request \
    "Edge Case: Different video, same tracker (1)" \
    "$PAYLOADS_DIR/edge_different_video_same_tracker_1.json" \
    "200" \
    "Should create different creative"

test_request \
    "Edge Case: Different video, same tracker (2)" \
    "$PAYLOADS_DIR/edge_different_video_same_tracker_2.json" \
    "200" \
    "Should create different creative"

# Тест 5: Invalid — отсутствует video_url
test_request \
    "Invalid: Missing video_url" \
    "$PAYLOADS_DIR/invalid_missing_video_url.json" \
    "400" \
    "Should reject missing field"

# Тест 6: Invalid — отсутствует tracker_id
test_request \
    "Invalid: Missing tracker_id" \
    "$PAYLOADS_DIR/invalid_missing_tracker_id.json" \
    "400" \
    "Should reject missing field"

# Тест 7: Invalid — пустой video_url
test_request \
    "Invalid: Empty video_url" \
    "$PAYLOADS_DIR/invalid_empty_video_url.json" \
    "400" \
    "Should reject empty field"

# Тест 8: Invalid — пустой tracker_id
test_request \
    "Invalid: Empty tracker_id" \
    "$PAYLOADS_DIR/invalid_empty_tracker_id.json" \
    "400" \
    "Should reject empty field"

# Тест 9: Invalid — неверный source_type
test_request \
    "Invalid: Wrong source_type" \
    "$PAYLOADS_DIR/invalid_wrong_source_type.json" \
    "400" \
    "Should reject wrong source_type"

# Тест 10: Garbage Input
test_request \
    "Garbage Input" \
    "$PAYLOADS_DIR/garbage_input.json" \
    "400" \
    "Should reject invalid payload"

# Итоги
echo ""
echo "=========================================="
echo "Test Results"
echo "=========================================="
echo "Total:  $TOTAL"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed! ✅${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed. ❌${NC}"
    exit 1
fi


