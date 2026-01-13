# Тестирование GenomAI

## Быстрый старт

```bash
# Локальная разработка
make up                    # Поднять сервисы
/e2e                       # Полный тест (42 проверки)
/e2e --quick               # Только health checks

# Перед PR
make test                  # Unit тесты (~15s)
/e2e                       # E2E тесты

# После деплоя
/e2e --prod                # Тест production
```

---

## Команды тестирования

### Make команды

| Команда | Время | Что делает |
|---------|-------|------------|
| `make test` | ~15s | Critical unit тесты |
| `make test-unit` | ~45s | Все unit тесты |
| `make test-integration` | ~2min | Integration тесты (требует DB) |
| `make ci` | ~60s | Полная CI симуляция |

### /e2e скилл

```bash
/e2e                    # Полный тест (14 фаз, 42 проверки)
/e2e --quick            # Phase 1: Health Checks
/e2e --workflows        # Phase 2-2.5: Workflow Tests
/e2e --contracts        # Phase 6: API Contract Testing
/e2e --security         # Phase 7: Security Testing
/e2e --db               # Phase 8: DB Constraints
/e2e --chaos            # Phase 9-10: Chaos + Concurrency
/e2e --functional       # Phase 11-13: Business Logic
/e2e --decision         # Phase 11: Decision Engine
/e2e --learning         # Phase 12: Learning Loop
/e2e --buyer            # Phase 13: Buyer Interactions
/e2e --prod             # Тест production (genomai.onrender.com)
```

---

## Фазы E2E тестирования

### Phase 1: Health Checks
- Decision Engine `/health`
- Supabase connection
- Temporal schedules (6 active)

### Phase 2: Workflow Live Tests
Триггерит и проверяет scheduled workflows:
- KeitaroPollerWorkflow
- MetricsProcessingWorkflow
- LearningLoopWorkflow
- MaintenanceWorkflow
- HealthCheckWorkflow
- DailyRecommendationWorkflow (SKIP — отправляет в Telegram)

### Phase 2.5: Event-Driven Workflows
Проверяет историю (без триггера):
- CreativePipelineWorkflow
- BuyerOnboardingWorkflow
- HistoricalImportWorkflow
- RecommendationDeliveryWorkflow

### Phase 3: Data Quality
- Creatives: video_url, status
- Ideas: canonical_hash (64 chars)
- Decisions: valid enum (approve/reject/defer)
- Hypotheses: content not empty

### Phase 4: Relationship Integrity
- Orphaned decomposed_creatives
- Decisions without traces
- Approved without hypothesis

### Phase 5: Learning Health
- Stale outcomes (learning_applied = false)
- Component learnings activity

### Phase 6: API Contract Testing
- Health endpoint (no auth)
- Metrics health endpoint
- Protected endpoint без auth → 401/403

### Phase 7: Security Testing
- Auth required
- Invalid token → 401/403
- No secrets in responses

### Phase 8: DB Constraints
- UNIQUE: decisions(idea_id, decision_epoch)
- FK: decomposed → creatives
- FK: decisions → ideas
- Hash integrity (64 chars)
- Valid decision enum

### Phase 9: Chaos/Resilience
- Circuit breaker events
- Retry exhausted hypotheses
- Stuck workflows (<30 min)
- Unhandled failures

### Phase 10: Concurrent Access
- Duplicate ideas (same hash)
- Duplicate outcome aggregates
- Learning applied multiple times

### Phase 11: Decision Engine Logic
- Decision idempotency
- Trace completeness
- Hard dead → no approves

### Phase 12: Learning Loop Logic
- Confidence bounds [0.0, 1.0]
- Learning idempotency (source_outcome_id)
- Outcome processing (<4h)

### Phase 13: Buyer Interactions
- Valid buyer states
- Stuck onboarding (<2h)
- Buyer data completeness

---

## Unit тесты

Расположение: `decision-engine-service/tests/unit/`

| Файл | Что тестирует |
|------|---------------|
| test_hashing.py | canonical_hash, avatar_hash |
| test_schema_validator.py | Canonical Schema validation |
| test_exploration.py | Thompson Sampling |
| test_outcome_service.py | Window ID (D1/D3/D7), CPA |
| test_circuit_breaker.py | Circuit breaker states |
| test_learning_idempotency.py | source_outcome_id check |
| test_module_extraction.py | Module extraction |
| test_modular_generation.py | Modular hypothesis |
| test_premise_extraction.py | Premise extraction |
| test_geo_validation.py | Geo validation |
| test_staleness_detector.py | Staleness detection |
| test_activity_validators.py | Temporal activity validation |

---

## Integration тесты

Расположение: `tests/integration/`

| Файл | Что тестирует |
|------|---------------|
| test_creative_pipeline.py | creative → decomposition → decision |
| test_learning_pipeline.py | outcome → confidence update |
| test_full_pipeline_e2e.py | Полный цикл |

---

## Когда что запускать

| Ситуация | Команда |
|----------|---------|
| Написал код | `make test` |
| Перед коммитом | `make test-unit` (pre-commit hook) |
| Перед PR | `/e2e` |
| После merge в develop | `/e2e` |
| После деплоя | `/e2e --prod` |
| Проблемы с workflow | `/e2e --workflows` |
| Проблемы с данными | `/e2e --db` |
| Проблемы с security | `/e2e --security` |

---

## QA Notes

Каждая задача требует `qa-notes/issue-XXX-*.md` с секцией `## Test`:

```markdown
## Что изменено
- Описание изменений

## Test
\`\`\`bash
curl -sf localhost:10000/endpoint | jq .status
\`\`\`
```

`task-done.sh` автоматически:
1. Находит qa-notes
2. Парсит команду из `## Test`
3. Выполняет на localhost
4. Блокирует PR если exit code != 0

---

## CI Pipeline

```yaml
stages:
  1. lint        # ruff check
  2. unit-tests  # make test-unit
  3. contracts   # validate_contracts.py
```

Триггеры:
- Push → lint + unit
- PR to develop → lint + unit + contracts
- Merge to main → full CI

---

## Troubleshooting

### Тесты падают на Supabase
```bash
# Проверить подключение
curl -sf "$SUPABASE_URL/rest/v1/" -H "apikey: $SUPABASE_ANON_KEY"
```

### Тесты падают на Temporal
```bash
# Проверить schedules
cd decision-engine-service && python -m temporal.schedules list
```

### Flaky тесты
```bash
# Запустить конкретный тест
pytest tests/unit/test_hashing.py -v

# С timeout
pytest tests/unit/test_hashing.py --timeout=30
```

---

## Карта процессов

Полная карта всех 15 процессов системы: [01_PROCESS_MAP.md](testing/01_PROCESS_MAP.md)

Включает:
- P1-P15: Все процессы с flow диаграммами
- Внешние интеграции (8 штук)
- Temporal workflows (15 штук)
- API endpoints (37+)
- Критические бизнес-правила
