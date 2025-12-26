#!/bin/bash
#
# Run Full Pipeline E2E Tests
#
# Prerequisites:
# - SUPABASE_SERVICE_ROLE_KEY set
# - API_KEY set (for Decision Engine)
# - Test creative registered with tracker_id=99999
#
# Usage:
#   ./scripts/run_e2e_test.sh           # Run all E2E tests
#   ./scripts/run_e2e_test.sh --quick   # Run health checks only
#   ./scripts/run_e2e_test.sh --step N  # Run specific step (1-10)
#
# Environment:
#   E2E_TRACKER_ID=54321  # Override default tracker_id (99999)
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "============================================================"
echo "GenomAI Full Pipeline E2E Test"
echo "============================================================"
echo ""

# Check environment
if [ -z "$SUPABASE_SERVICE_ROLE_KEY" ]; then
    echo -e "${YELLOW}Warning: SUPABASE_SERVICE_ROLE_KEY not set${NC}"
    echo "Tests requiring database access will fail."
    echo ""
fi

if [ -z "$API_KEY" ]; then
    echo -e "${YELLOW}Warning: API_KEY not set${NC}"
    echo "Decision Engine tests will fail."
    echo ""
fi

# Parse arguments
QUICK_MODE=false
STEP=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --quick)
            QUICK_MODE=true
            shift
            ;;
        --step)
            STEP="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Run tests
cd "$(dirname "$0")/.."

if [ "$QUICK_MODE" = true ]; then
    echo "Running quick health checks..."
    python -m pytest tests/integration/test_full_pipeline_e2e.py::TestPipelineHealthChecks -v
elif [ -n "$STEP" ]; then
    echo "Running step $STEP..."
    python -m pytest tests/integration/test_full_pipeline_e2e.py::TestFullPipelineE2E::test_step${STEP}_ -v
else
    echo "Running full E2E test suite..."
    echo ""
    echo "Test Steps:"
    echo "  1. Creative Registration"
    echo "  2. Transcription"
    echo "  3. Decomposition"
    echo "  4. Idea Creation"
    echo "  5. Decision Engine"
    echo "  6. Hypothesis Generation"
    echo "  7. Telegram Delivery"
    echo "  8. Keitaro Metrics"
    echo "  9. Snapshot & Outcome"
    echo " 10. Learning Loop"
    echo ""

    python -m pytest tests/integration/test_full_pipeline_e2e.py -v --tb=short
fi

echo ""
echo -e "${GREEN}Test run complete.${NC}"
