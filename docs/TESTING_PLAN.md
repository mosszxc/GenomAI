# System Capabilities Testing Plan

Полный план тестирования 126 capabilities, разбитый на 3 параллельные части.

---

## Распределение

| Part | Сферы | Capabilities | Фокус |
|------|-------|--------------|-------|
| 1 | Ingestion, Decomposition, Idea Registry, Metrics, Outcomes | 47 | Data Pipeline |
| 2 | Decision Engine, Hypothesis Factory, Recommendations, Learning | 46 | Core Logic |
| 3 | Buyer, Delivery, Historical, Infrastructure, Errors, Security | 43 | Interface & Support |

---

## PART 1: Data Pipeline (47 capabilities)

### Сферы
- Video Ingestion (13)
- Decomposition (12)
- Idea Registry (8)
- Metrics (8)
- Outcomes (6)

### Pre-requisites
- Supabase доступ
- n8n workflows активны
- AssemblyAI credentials
- Keitaro API доступ

### Test Sequence

#### 1.1 Video Ingestion (ING-01 → ING-13)
```
Workflow: Buyer Creative Registration (d5i9dB2GNqsbfmSD)
Workflow: Creative Transcription (WMnFHqsFh8i7ddjV)
```

| ID | Test | SQL Check |
|----|------|-----------|
| ING-01 | Отправить видео в Telegram bot | `SELECT * FROM genomai.creatives ORDER BY created_at DESC LIMIT 1` |
| ING-02 | Отправить URL видео | Проверить video_url заполнен |
| ING-03 | Проверить buyer_id | `WHERE buyer_id IS NOT NULL` |
| ING-04 | Отправить тот же URL повторно | Счётчик creatives не увеличился |
| ING-05 | Event log | `SELECT * FROM genomai.event_log WHERE event_type = 'CreativeReceived'` |
| ING-10 | Транскрипция | `SELECT * FROM genomai.transcripts WHERE creative_id = '{id}'` |
| ING-11 | FK связь | `transcripts.creative_id` соответствует creative |
| ING-12 | Event log | `WHERE event_type = 'TranscriptCreated'` |
| ING-13 | Error handling | Отправить невалидное видео, проверить статус |

#### 1.2 Decomposition (DEC-01 → DEC-12)
```
Workflow: creative_decomposition_llm (mv6diVtqnuwr7qev)
```

| ID | Test | SQL Check |
|----|------|-----------|
| DEC-01 | 14 полей извлечены | `SELECT * FROM genomai.decomposed_creatives` - проверить все поля |
| DEC-02 | Schema validation | POST `/api/schema/validate` с payload |
| DEC-03 | Запись создана | `SELECT COUNT(*) FROM genomai.decomposed_creatives` |
| DEC-04 | FK связи | creative_id и idea_id заполнены |
| DEC-05 | Event log | `WHERE event_type = 'CreativeDecomposed'` |
| DEC-10 | Missing required | Отправить неполный payload → ошибка |
| DEC-11 | Invalid enum | Неверный angle_type → ошибка |
| DEC-12 | v2 schema | Отправить v2 payload → успех |

#### 1.3 Idea Registry (IDR-01 → IDR-11)
```
Workflow: idea_registry_create (cGSyJPROrkqLVHZP)
```

| ID | Test | SQL Check |
|----|------|-----------|
| IDR-01 | Idea создана | `SELECT * FROM genomai.ideas ORDER BY created_at DESC LIMIT 1` |
| IDR-02 | Hash генерируется | `canonical_hash IS NOT NULL` |
| IDR-03 | Идемпотентность | Повторный запрос → та же idea |
| IDR-04 | Status = active | `status = 'active'` |
| IDR-05 | death_state = alive | `death_state = 'alive'` |
| IDR-06 | Event log | `WHERE event_type = 'IdeaCreated'` |
| IDR-10 | API endpoint | POST `/api/idea-registry/register` → idea_id |
| IDR-11 | Avatar linking | Если avatar определён → avatar_id заполнен |

#### 1.4 Metrics (MET-01 → MET-12)
```
Workflow: Keitaro Poller (0TrVJOtHiNEEAsTN)
Workflow: Snapshot Creator (Gii8l2XwnX43Wqr4)
```

| ID | Test | SQL Check |
|----|------|-----------|
| MET-01 | Polling работает | `SELECT * FROM genomai.raw_metrics_current` |
| MET-02 | Mapping creative_id | creative_id = campaign_id в Keitaro |
| MET-03 | Все поля | clicks, conversions, spend, revenue NOT NULL |
| MET-04 | Event log | `WHERE event_type = 'RawMetricsObserved'` |
| MET-10 | Snapshot создан | `SELECT * FROM genomai.daily_metrics_snapshot` |
| MET-11 | Immutable | Попытка UPDATE → ошибка |
| MET-12 | Event log | `WHERE event_type = 'DailyMetricsSnapshotCreated'` |

#### 1.5 Outcomes (OUT-01 → OUT-11)
```
Workflow: Outcome Processor (bbbQC4Aua5E3SYSK)
Workflow: Outcome Aggregator (243QnGrUSDtXLjqU)
```

| ID | Test | SQL Check |
|----|------|-----------|
| OUT-01 | Outcome создан | `SELECT * FROM genomai.outcome_aggregates` |
| OUT-02 | CPA расчёт | `cpa = spend / conversions` |
| OUT-03 | Environment | `environment_ctx` содержит geo, vertical |
| OUT-04 | origin_type | `origin_type = 'system'` |
| OUT-10 | Aggregation API | POST `/api/outcomes/aggregate` |
| OUT-11 | Service layer | outcome_service.py обрабатывает запрос |

### Part 1 Verification Query
```sql
SELECT
  (SELECT COUNT(*) FROM genomai.creatives) as creatives,
  (SELECT COUNT(*) FROM genomai.transcripts) as transcripts,
  (SELECT COUNT(*) FROM genomai.decomposed_creatives) as decomposed,
  (SELECT COUNT(*) FROM genomai.ideas) as ideas,
  (SELECT COUNT(*) FROM genomai.raw_metrics_current) as metrics,
  (SELECT COUNT(*) FROM genomai.outcome_aggregates) as outcomes;
```

---

## PART 2: Core Logic (46 capabilities)

### Сферы
- Decision Engine (18)
- Hypothesis Factory (4)
- Recommendations (10)
- Learning (14)

### Pre-requisites
- Decision Engine на Render активен
- Part 1 выполнен (есть ideas)
- API_KEY доступен

### Test Sequence

#### 2.1 Decision Engine (DE-01 → DE-42)
```
Endpoint: POST /api/decision/
Workflow: decision_engine_mvp (YT2d7z5h9bPy1R4v)
```

| ID | Test | Verification |
|----|------|--------------|
| DE-01 | POST с valid idea_id | Response содержит decision + trace |
| DE-02 | 4 checks в trace | `len(trace.checks) == 4` |
| DE-03 | First fail stops | При fail check_1 → checks 2-4 не выполнены |
| DE-04 | Decision saved | `SELECT * FROM genomai.decisions WHERE idea_id = '{id}'` |
| DE-05 | Trace saved | `SELECT * FROM genomai.decision_traces` |
| DE-06 | Event log | `WHERE event_type = 'DecisionMade'` |

**Check 1: Schema Validity**
| ID | Test | Expected |
|----|------|----------|
| DE-10 | Valid idea | `result = 'PASSED'` |
| DE-11 | Invalid idea (no hash) | `decision_type = 'reject', reason = 'schema_invalid'` |

**Check 2: Death Memory**
| ID | Test | Expected |
|----|------|----------|
| DE-20 | Alive idea | `result = 'PASSED'` |
| DE-21 | Dead idea | `decision_type = 'reject', reason = 'idea_dead'` |

**Check 3: Fatigue Constraint**
| ID | Test | Expected |
|----|------|----------|
| DE-30 | MVP mode | `result = 'PASSED', note = 'MVP not implemented'` |

**Check 4: Risk Budget**
| ID | Test | Expected |
|----|------|----------|
| DE-40 | Under limit | `result = 'PASSED'` |
| DE-41 | Over limit | `decision_type = 'defer', reason = 'risk_budget_exceeded'` |
| DE-42 | Default limit | max_active_ideas = 100 |

**Decision Types**
| Type | Test | Next Step |
|------|------|-----------|
| APPROVE | All 4 PASSED | → Hypothesis Factory |
| REJECT | Check 1/2/3 FAILED | Идея не используется |
| DEFER | Check 4 FAILED | Повторить позже |

#### 2.2 Hypothesis Factory (HF-01 → HF-04)
```
Workflow: hypothesis_factory_generate (oxG1DqxtkTGCqLZi)
```

| ID | Test | SQL Check |
|----|------|-----------|
| HF-01 | Hypothesis создана | `SELECT * FROM genomai.hypotheses WHERE idea_id = '{id}'` |
| HF-02 | FK связи | idea_id, decision_id заполнены |
| HF-03 | Status = pending | `status = 'pending'` |
| HF-04 | Event log | `WHERE event_type = 'HypothesisCreated'` |

#### 2.3 Recommendations (REC-01 → REC-14)
```
Endpoint: POST /recommendations/generate
```

| ID | Test | Verification |
|----|------|--------------|
| REC-01 | Generate | Response содержит recommendation с компонентами |
| REC-02 | Exploitation 75% | Запустить 100 раз → ~75 exploitation |
| REC-03 | Exploration 25% | ~25 exploration |
| REC-04 | Filtering | Передать buyer, geo, vertical → релевантные результаты |
| REC-10 | GET /recommendations/ | Список pending |
| REC-11 | GET /recommendations/{id} | Конкретная рекомендация |
| REC-12 | POST /{id}/executed | Привязать creative_id |
| REC-13 | POST /{id}/outcome | Записать результат |
| REC-14 | GET /recommendations/stats | Статистика |

#### 2.4 Learning (LRN-01 → LRN-30)
```
Endpoint: POST /learning/process
Workflow: Learning Loop v2 (fzXkoG805jQZUR3S)
```

**Confidence Updates**
| ID | Test | Verification |
|----|------|--------------|
| LRN-01 | Process outcomes | POST `/learning/process` → success |
| LRN-02 | CPA < 20 | confidence += 0.1 |
| LRN-03 | CPA >= 20 | confidence -= 0.15 |
| LRN-04 | Time decay | Старые outcomes меньше влияют |
| LRN-05 | Environment weighting | Контекст влияет на delta |
| LRN-06 | Versioning | `SELECT * FROM genomai.idea_confidence_versions` |

**Death Detection**
| ID | Test | Verification |
|----|------|--------------|
| LRN-10 | 3 failures | `death_state = 'soft_dead'` |
| LRN-11 | 5 failures | `death_state = 'hard_dead'` |
| LRN-12 | Death blocks | DE Check 2 → REJECT |

**Component Learning**
| ID | Test | Verification |
|----|------|--------------|
| LRN-20 | Component learnings | `SELECT * FROM genomai.component_learnings` |
| LRN-21 | Avatar learnings | `SELECT * FROM genomai.avatar_learnings` |
| LRN-22 | Usage in recommendations | High winning_rate → exploit |
| LRN-30 | Status endpoint | GET `/learning/status` → pending count |

### Part 2 Verification Query
```sql
SELECT
  (SELECT COUNT(*) FROM genomai.decisions) as decisions,
  (SELECT COUNT(*) FROM genomai.decision_traces) as traces,
  (SELECT COUNT(*) FROM genomai.hypotheses) as hypotheses,
  (SELECT COUNT(*) FROM genomai.recommendations) as recommendations,
  (SELECT COUNT(*) FROM genomai.idea_confidence_versions) as confidence_versions,
  (SELECT COUNT(*) FROM genomai.component_learnings) as component_learnings;
```

---

## PART 3: Interface & Support (43 capabilities)

### Сферы
- Buyer System (14)
- Delivery (7)
- Historical Import (4)
- Infrastructure (8)
- Error Handling (6)
- Security (4)

### Pre-requisites
- Telegram bot доступен
- Telegram credentials в n8n
- Test buyer chat_id

### Test Sequence

#### 3.1 Buyer System (BUY-01 → BUY-30)
```
Workflow: Telegram Router (BuyQncnHNb7ulL6z)
Workflow: Buyer Onboarding (hgTozRQFwh4GLM0z)
```

**Onboarding**
| ID | Test | SQL Check |
|----|------|-----------|
| BUY-01 | /start → State machine | `SELECT * FROM genomai.buyer_states` |
| BUY-02 | Собраны все поля | name, geos[], verticals[], keitaro_source |
| BUY-03 | Multi-geo | `geos = ARRAY['US', 'DE']` |
| BUY-04 | Multi-vertical | `verticals = ARRAY['dating', 'nutra']` |
| BUY-05 | State persistence | buyer_states обновляется |

**Commands**
| ID | Test | Expected |
|----|------|----------|
| BUY-10 | /start | Начало онбординга |
| BUY-11 | /stats | Статистика buyer'а |
| BUY-12 | /help | Справка (в любом состоянии) |

**Interaction Logging**
| ID | Test | SQL Check |
|----|------|-----------|
| BUY-20 | Logging | `SELECT * FROM genomai.buyer_interactions` |
| BUY-21 | Direction | `direction IN ('in', 'out')` |
| BUY-22 | Message type | `message_type IN ('text', 'video', 'command')` |

**Daily Digest**
| ID | Test | Expected |
|----|------|----------|
| BUY-30 | Digest отправлен | Сообщение в Telegram |

#### 3.2 Delivery (DEL-01 → DEL-12)
```
Workflow: Telegram Hypothesis Delivery (5q3mshC9HRPpL6C0)
Workflow: Recommendation Delivery (QC8bmnAYdH5mkntG)
```

**Telegram Delivery**
| ID | Test | Verification |
|----|------|--------------|
| DEL-01 | Hypothesis доставлена | Сообщение в Telegram |
| DEL-02 | Форматирование | % confidence видно |
| DEL-03 | Запись | `SELECT * FROM genomai.deliveries` |
| DEL-04 | Event log | `WHERE event_type = 'HypothesisDelivered'` |

**Recommendation Delivery**
| ID | Test | Verification |
|----|------|--------------|
| DEL-10 | Recommendation доставлена | Сообщение в Telegram |
| DEL-11 | Type указан | exploit/explore видно |
| DEL-12 | Avatar указан | Имя и desire |

#### 3.3 Historical Import (HIS-01 → HIS-04)
```
Workflow: Historical Creative Import (1FC7amTd3dCRZPEa)
Workflow: Buyer Historical Loader (lmiWkYTRZPSpydJH)
```

| ID | Test | SQL Check |
|----|------|-----------|
| HIS-01 | Batch URLs | Отправить 5 URLs → все обработаны |
| HIS-02 | Queue | `SELECT * FROM genomai.historical_import_queue` |
| HIS-03 | origin_type | `origin_type = 'historical'` |
| HIS-04 | Buyer mapping | keitaro_source связывает buyer |

#### 3.4 Infrastructure (INF-01 → INF-22)

**Health & Monitoring**
| ID | Test | Verification |
|----|------|--------------|
| INF-01 | GET /health | `{"status": "ok"}` |
| INF-02 | Keep-alive | Workflow запускается каждые 10 мин |
| INF-03 | Retry logic | 3x15s после cold start |

**Event Log**
| ID | Test | SQL Check |
|----|------|-----------|
| INF-10 | All events logged | `SELECT event_type, COUNT(*) FROM genomai.event_log GROUP BY 1` |
| INF-11 | Immutable | `UPDATE genomai.event_log SET...` → error |

**Database Constraints**
| ID | Test | Expected |
|----|------|----------|
| INF-20 | Generated columns | INSERT win_rate → error |
| INF-21 | FK constraints | Invalid FK → error |
| INF-22 | CHECK constraints | Invalid origin_type + decision_id → error |

#### 3.5 Error Handling (ERR-01 → ERR-11)

**API Errors**
| ID | Test | Expected |
|----|------|----------|
| ERR-01 | 400 Bad Request | Невалидный JSON |
| ERR-02 | 401 Unauthorized | Без API_KEY |
| ERR-03 | 404 Not Found | Несуществующий idea_id |
| ERR-04 | 500 Internal | Unhandled exception |

**n8n Error Handling**
| ID | Test | Expected |
|----|------|----------|
| ERR-10 | Error workflow | Уведомление при ошибке |
| ERR-11 | continueOnFail | Graceful degradation |

#### 3.6 Security (SEC-01 → SEC-11)

**Authentication**
| ID | Test | Expected |
|----|------|----------|
| SEC-01 | Bearer token | 401 без токена на всех endpoints (кроме /health) |
| SEC-02 | Service role | Не anon key |

**Data Protection**
| ID | Test | Expected |
|----|------|----------|
| SEC-10 | No credentials in code | grep -r "SUPABASE" → только env refs |
| SEC-11 | Schema isolation | genomai schema, не public |

### Part 3 Verification Query
```sql
SELECT
  (SELECT COUNT(*) FROM genomai.buyers) as buyers,
  (SELECT COUNT(*) FROM genomai.buyer_interactions) as interactions,
  (SELECT COUNT(*) FROM genomai.deliveries) as deliveries,
  (SELECT COUNT(*) FROM genomai.historical_import_queue) as import_queue,
  (SELECT COUNT(*) FROM genomai.event_log) as events;
```

---

## Execution Commands

### Run Part 1: Data Pipeline
```bash
# Отдельный агент
/test-part-1
```

### Run Part 2: Core Logic
```bash
# Отдельный агент
/test-part-2
```

### Run Part 3: Interface & Support
```bash
# Отдельный агент
/test-part-3
```

### Run All Parts (Parallel)
```bash
# Запустить все 3 части параллельно
/test-full
```

---

## Test Data Requirements

| Part | Test Data Needed |
|------|-----------------|
| 1 | Video file, Video URL, Keitaro campaign |
| 2 | idea_id from Part 1, outcomes in DB |
| 3 | Telegram chat_id, historical URLs |

---

## Success Criteria

| Part | Pass Criteria |
|------|---------------|
| 1 | Все 47 capabilities verified, data in DB |
| 2 | Все 46 capabilities verified, decisions flow works |
| 3 | Все 43 capabilities verified, Telegram works |

**Full System Pass**: All 126 capabilities verified
