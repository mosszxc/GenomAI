# Makefile for GenomAI
# Usage: make <target>

.PHONY: help install lint format mypy test test-unit test-slow test-all test-integration e2e e2e-quick setup-hooks ci pre-commit-check pre-push-check issues issue-start issue-ready issues-critical issues-by-priority up down dev dev-stop

# Default target
help:
	@echo "GenomAI Test Commands"
	@echo "====================="
	@echo ""
	@echo "Setup:"
	@echo "  make install        - Install dependencies"
	@echo "  make setup-hooks    - Install git hooks"
	@echo ""
	@echo "Local Dev:"
	@echo "  make up             - Start all (Temporal + Worker + FastAPI)"
	@echo "  make down           - Stop all"
	@echo "  make dev            - Start FastAPI only"
	@echo ""
	@echo "Linting:"
	@echo "  make lint           - Run ruff check with auto-fix"
	@echo "  make format         - Run ruff format"
	@echo "  make mypy           - Run type checking (gradual mode)"
	@echo ""
	@echo "Testing:"
	@echo "  make test           - Run critical tests only (~15s)"
	@echo "  make test-unit      - Run all unit tests (~45s)"
	@echo "  make test-slow      - Run slow unit tests"
	@echo "  make test-all       - Run unit + contract validation (~60s)"
	@echo "  make test-integration - Run integration tests (requires env)"
	@echo ""
	@echo "E2E (server):"
	@echo "  make e2e-quick      - Health checks only (~30s)"
	@echo "  make e2e            - Full E2E flow (~5min)"
	@echo ""
	@echo "CI Simulation:"
	@echo "  make ci             - Simulate full CI pipeline locally"
	@echo "  make pre-commit-check - Run pre-commit hooks manually"
	@echo "  make pre-push-check   - Run pre-push hooks manually"
	@echo ""
	@echo "Issue Management:"
	@echo "  make issues         - Dashboard: ready, in-progress"
	@echo "  make issue-start N=123 - Start working on issue #123"
	@echo "  make issue-ready N=123 - Mark issue as ready"
	@echo "  make issues-critical   - List CRITICAL issues"
	@echo "  make issues-by-priority - List by CRITICAL/HIGH/MEDIUM"

# ============ Setup ============

install:
	cd decision-engine-service && pip install -r requirements.txt
	pip install pytest pytest-asyncio pytest-timeout pre-commit ruff

setup-hooks:
	pre-commit install
	pre-commit install --hook-type pre-push
	@echo ""
	@echo "Git hooks installed successfully!"
	@echo "pre-commit: lint + format + critical tests"
	@echo "pre-push: all unit tests"

# ============ Local Dev ============

up:
	@./scripts/dev-up.sh

down:
	@./scripts/dev-down.sh

dev:
	@./scripts/local-dev.sh

dev-stop:
	@for pf in /tmp/genomai-dev/server-*.pid; do \
		[ -f "$$pf" ] || continue; \
		pid=$$(cat "$$pf"); \
		kill "$$pid" 2>/dev/null && echo "Stopped server (PID: $$pid)" || true; \
		rm -f "$$pf"; \
	done

# ============ Linting ============

lint:
	python3 -m ruff check decision-engine-service/ --fix

format:
	python3 -m ruff format decision-engine-service/

format-check:
	python3 -m ruff format decision-engine-service/ --check

# Type checking with mypy (gradual mode)
mypy:
	@python3 -c "import mypy" 2>/dev/null || (echo "Installing mypy..." && pip install mypy types-requests)
	cd decision-engine-service && python3 -m mypy src/ --config-file=pyproject.toml

# ============ Unit Tests ============

# Critical tests only - same as pre-commit
test:
	cd decision-engine-service && python3 -m pytest tests/unit/test_hashing.py tests/unit/test_schema_validator.py -q --tb=short --timeout=30

# All unit tests (not slow) - same as pre-push
test-unit:
	@python3 -c "import pytest" 2>/dev/null || (echo "ERROR: pytest not installed. Run: make install" && exit 1)
	cd decision-engine-service && python3 -m pytest tests/unit/ -v --tb=short -m "not slow" --timeout=60

# Slow unit tests
test-slow:
	cd decision-engine-service && python3 -m pytest tests/unit/ -v --tb=short -m "slow" --timeout=120

# All tests (unit + contracts)
test-all: test-unit
	@if [ -f scripts/validate_contracts.py ]; then \
		python3 scripts/validate_contracts.py --verbose; \
	else \
		echo "Contract validation skipped (scripts/validate_contracts.py not found)"; \
	fi

# ============ Integration Tests ============

# Requires: SUPABASE_SERVICE_ROLE_KEY, API_KEY
test-integration:
	@if [ -z "$$SUPABASE_SERVICE_ROLE_KEY" ]; then \
		echo "ERROR: SUPABASE_SERVICE_ROLE_KEY not set"; \
		echo "Set environment variables or use: source .env.test"; \
		exit 1; \
	fi
	python3 -m pytest tests/integration/ -v --tb=short -m "integration and not slow"

# ============ E2E Tests (Server) ============

# Quick health checks
e2e-quick:
	@echo "=== E2E Quick Health Check ==="
	@echo ""
	@echo "1. Decision Engine health..."
	@curl -s -o /dev/null -w "   Status: %{http_code}\n" https://genomai.onrender.com/health || echo "   FAILED"
	@echo ""
	@echo "2. Checking for stuck pipelines..."
	@echo "   (Run: SELECT status, count(*) FROM genomai.creatives GROUP BY status)"
	@echo ""
	@echo "=== Quick check complete ==="
	@echo "For full E2E: make e2e"

# Full E2E (see docs/E2E_SERVER_CHECKLIST.md)
e2e:
	@echo "=== Full E2E Test ==="
	@echo ""
	@echo "Follow the checklist: docs/E2E_SERVER_CHECKLIST.md"
	@echo ""
	@echo "Quick summary:"
	@echo "1. Health check: curl https://genomai.onrender.com/health"
	@echo "2. Trigger test creative via Telegram or webhook"
	@echo "3. Verify pipeline: creative -> transcript -> decomposition -> decision"
	@echo "4. Check DB for results"
	@echo ""
	@if [ -f scripts/run_e2e_test.sh ]; then \
		./scripts/run_e2e_test.sh; \
	else \
		echo "Automated E2E script not found. Follow manual checklist."; \
	fi

# ============ Issue Management ============

# Show all issues by status
issues:
	@echo "=== Issues Dashboard ==="
	@echo ""
	@echo "📌 IN PROGRESS:"
	@gh issue list -l "status:in-progress" --json number,title --template '{{range .}}  #{{.number}} {{.title}}{{"\n"}}{{end}}' || true
	@echo ""
	@echo "🟢 READY:"
	@gh issue list -l "status:ready" --json number,title --template '{{range .}}  #{{.number}} {{.title}}{{"\n"}}{{end}}' || true

# Start working on an issue (label set automatically by task-start.sh)
issue-start:
	@if [ -z "$(N)" ]; then echo "Usage: make issue-start N=123"; exit 1; fi
	./scripts/task-start.sh $(N)

# Mark issue as ready
issue-ready:
	@if [ -z "$(N)" ]; then echo "Usage: make issue-ready N=123"; exit 1; fi
	gh issue edit $(N) --add-label "status:ready" --remove-label "status:in-progress"

# List critical issues (ARCH-CRITICAL, CRITICAL)
issues-critical:
	@echo "=== CRITICAL Issues ==="
	@gh issue list --search "CRITICAL in:title" --json number,title,labels --template '{{range .}}#{{.number}} {{.title}}{{"\n"}}{{end}}'

# List issues by priority
issues-by-priority:
	@echo "=== CRITICAL ==="
	@gh issue list --search "CRITICAL in:title" --json number,title --template '{{range .}}  #{{.number}} {{.title}}{{"\n"}}{{end}}'
	@echo ""
	@echo "=== HIGH ==="
	@gh issue list --search "HIGH in:title" --json number,title --template '{{range .}}  #{{.number}} {{.title}}{{"\n"}}{{end}}'
	@echo ""
	@echo "=== MEDIUM ==="
	@gh issue list --search "MEDIUM in:title" --json number,title --template '{{range .}}  #{{.number}} {{.title}}{{"\n"}}{{end}}'

# ============ CI Simulation ============

# Simulate full CI locally
ci: lint format-check test-unit
	@if [ -f scripts/validate_contracts.py ]; then \
		python3 scripts/validate_contracts.py --verbose; \
	fi
	@echo ""
	@echo "=== CI simulation complete. All checks passed. ==="

# Pre-commit simulation
pre-commit-check:
	pre-commit run --all-files

# Pre-push simulation
pre-push-check:
	pre-commit run --all-files --hook-stage pre-push

# ============ Supabase Local ============

supabase-start:
	supabase start

supabase-stop:
	supabase stop

supabase-reset:
	supabase db reset

supabase-status:
	supabase status

# Full local environment (Supabase + FastAPI)
local:
	./scripts/local-full.sh

local-reset:
	./scripts/local-full.sh --reset

# Environment switching
env-local:
	@echo "Run: source scripts/env-switch.sh local"

env-prod:
	@echo "Run: source scripts/env-switch.sh prod"

env-status:
	@source scripts/env-switch.sh status

# ============ Release ============

release:
	./scripts/release.sh

release-dry:
	./scripts/release.sh --dry-run
