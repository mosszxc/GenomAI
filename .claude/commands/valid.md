# Process Validation

Полная валидация бизнес-процесса GenomAI: workflows → API → DB → events.

## Использование

```
/valid {process_name}
```

## Процессы

### 1. learning-loop

**Описание:** Keitaro clicks → Outcome Aggregator → Learning API → Signals

**Компоненты:**
| Тип | ID/Endpoint | Таблица |
|-----|-------------|---------|
| Workflow | `0TrVJOtHiNEEAsTN` (Keitaro Poller) | `raw_clicks` |
| Workflow | `243QnGrUSDtXLjqU` (Outcome Aggregator) | `outcomes` |
| API | `POST /learning/process` | `learning_signals` |
| Events | — | `LearningProcessed`, `OutcomeAggregated` |

**Тест:**
1. Проверить последние raw_clicks
2. Trigger Outcome Aggregator
3. POST /learning/process
4. Verify learning_signals создан

---

### 2. hypothesis-factory

**Описание:** Idea → Decision Engine → Hypothesis → Telegram

**Компоненты:**
| Тип | ID/Endpoint | Таблица |
|-----|-------------|---------|
| API | `POST /api/decision/` | `decisions` |
| Workflow | `oxG1DqxtkTGCqLZi` (hypothesis_factory_generate) | `hypotheses` |
| Workflow | `5q3mshC9HRPpL6C0` (Telegram Delivery) | `deliveries` |
| Events | — | `HypothesisGenerated`, `HypothesisDelivered` |

**Тест:**
1. Найти idea с status=pending
2. POST /api/decision/
3. Verify decision created
4. Trigger hypothesis_factory
5. Verify hypothesis status=ready_for_launch
6. Trigger Telegram Delivery
7. Verify HypothesisDelivered event

---

### 3. video-ingestion

**Описание:** YouTube URL → Transcript → Ideas extraction

**Компоненты:**
| Тип | ID/Endpoint | Таблица |
|-----|-------------|---------|
| Workflow | `sI4IC9COxKImki7e` (Video Ingest) | `videos`, `transcripts` |
| Workflow | (ideas extraction) | `ideas` |
| Events | — | `VideoIngested`, `IdeasExtracted` |

**Тест:**
1. Trigger Video Ingest с test URL
2. Verify video + transcript created
3. Verify ideas extracted

---

### 4. decision-engine

**Описание:** Idea → 4 checks → APPROVE/REJECT/DEFER

**Компоненты:**
| Тип | ID/Endpoint | Таблица |
|-----|-------------|---------|
| API | `POST /api/decision/` | `decisions` |
| API | `GET /health` | — |
| Checks | schema, death_memory, fatigue, risk | — |

**Тест:**
1. GET /health → status ok
2. POST /api/decision/ с test idea
3. Verify decision + reasoning

---

## Инструкции по валидации

### Phase 1: REVIEW (для каждого workflow)

```
mcp__n8n-mcp__n8n_get_workflow(id: workflow_id, mode: "full")
```

**Checklist:**
- [ ] Credentials present (Supabase: `RNItSRYOCypd9H1a`, Telegram: `06SWHhdUxiQNwDWD`)
- [ ] Supabase update имеет filters
- [ ] If nodes правильно connected
- [ ] Expressions имеют fallback для null

### Phase 2: TEST (end-to-end)

Запустить процесс от начала до конца:

```javascript
// Пример для hypothesis-factory
1. mcp__supabase__execute_sql("SELECT id FROM genomai.ideas WHERE status='pending' LIMIT 1")
2. WebFetch POST genomai.onrender.com:10000/api/decision/ {idea_id: ...}
3. mcp__n8n-mcp__n8n_test_workflow(oxG1DqxtkTGCqLZi, {idea_id: ...})
4. mcp__n8n-mcp__n8n_test_workflow(5q3mshC9HRPpL6C0, {idea_id: ...})
```

### Phase 3: VERIFY

```sql
-- Проверить все таблицы процесса
SELECT * FROM genomai.{table} ORDER BY created_at DESC LIMIT 3;

-- Проверить события
SELECT event_type, entity_id, occurred_at
FROM genomai.event_log
WHERE event_type IN ('Event1', 'Event2')
ORDER BY occurred_at DESC LIMIT 5;
```

### Phase 4: REPORT

```markdown
## Process Validation: {process_name}

### Components Status
| Component | Type | Status | Details |
|-----------|------|--------|---------|
| Keitaro Poller | workflow | OK | active, no issues |
| Outcome Aggregator | workflow | WARN | missing credential |
| /learning/process | API | OK | 200 response |

### Data Flow
| Step | Table | Records | Status |
|------|-------|---------|--------|
| 1 | raw_clicks | 150 | OK |
| 2 | outcomes | 45 | OK |
| 3 | learning_signals | 12 | OK |

### Events
| Event | Count (24h) | Last |
|-------|-------------|------|
| OutcomeAggregated | 5 | 2h ago |
| LearningProcessed | 3 | 4h ago |

### VERDICT: PASS / FAIL
```

## Auto-fix

При обнаружении проблем:
1. Missing credentials → добавить автоматически
2. Missing filters → добавить `id` filter
3. Broken connections → исправить branch naming

## Примеры

```bash
/valid learning-loop      # валидация полного learning loop
/valid hypothesis-factory # валидация генерации гипотез
/valid decision-engine    # проверка Decision Engine API
/valid video-ingestion    # проверка загрузки видео
```

## Когда применять

**Автоматически после:**
- Изменения любого workflow в процессе
- Деплоя новой версии API
- Миграции БД
- Жалобы "процесс не работает"

**Вручную:**
- `/valid {process}` — полная проверка
- `/valid {process} --review-only` — только review без тестов
