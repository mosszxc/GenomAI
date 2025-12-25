# GenomAI — Implementation Checklist (Post-Architecture)
Версия: v1.0
Статус: IMPLEMENTATION / EXECUTION
Scope: MVP
Основан на:
ARCHITECTURE_LOCK, EVENT_MODEL v1.1, STORAGE_MODEL, ERROR_HANDLING,
TECH_DECISIONS v1.2, DATA_SCHEMAS, API_CONTRACTS

## 0. Правило начала

❗ **К реализации можно приступать только если:**
- Layer 0–4 документы зафиксированы
- структура /docs создана
- все документы находятся в правильных папках
- нет открытых архитектурных вопросов

## 1. Repo & Environment Setup

### 1.1 Репозиторий
- [ ] Создать репозиторий
- [ ] Добавить /docs со всеми слоями
- [ ] Зафиксировать версии документов (commit)

### 1.2 Supabase
- [ ] Создать проект
- [ ] Настроить PostgreSQL
- [ ] Создать схемы таблиц из DATA_SCHEMAS.md
- [ ] Проверить ограничения (unique, append-only)

### 1.3 Secrets & Config
- [ ] Telegram Bot Token
- [ ] Supabase credentials
- [ ] Keitaro API access
- [ ] LLM API key
- [ ] Transcription provider access

## 2. Event Infrastructure ✅ COMPLETED

### 2.1 Event Log ✅
- [x] Создать таблицу event_log
- [x] Реализовать idempotency guard
- [x] Запретить UPDATE / DELETE

### 2.2 Event Emission ✅
- [x] Функция emit_event(event_type, entity, payload)
- [x] Проверка idempotency_key
- [x] Логирование ошибок

**Статус:** ✅ **Event Infrastructure готова**
- Таблица: `genomai.event_log` - создана с индексами
- Append-only защита: триггеры работают
- Idempotency: индекс на `idempotency_key` создан

## 3. Ingestion & Creative Registration ✅ COMPLETED

### 3.1 Telegram → n8n ✅
- [x] Webhook для приёма video_url + tracker_id
- [x] Валидация payload
- [x] Генерация creative_id
- [x] Emit CreativeReferenceReceived

### 3.2 Creative Storage ✅
- [x] Insert в creatives
- [x] Проверка идемпотентности
- [x] Статус registered

**Статус:** ✅ **STEP 01 завершён и протестирован**
- Workflow: `creative_ingestion_webhook` (ID: `dvZvUUmhtPzYOK7X`) - активен
- Таблица: `genomai.creatives` - создана и протестирована
- События: `CreativeReferenceReceived`, `CreativeRegistered`, `CreativeIngestionRejected` - реализованы
- Тестирование: все проверки из playbook пройдены
- Epic: #1 - закрыт

## 4. Transcription Pipeline ✅ COMPLETED
- [x] Триггер транскрипции
- [x] Получение результата (AssemblyAI polling)
- [x] Запись в transcripts (version = 1)
- [x] Emit TranscriptCreated

**Статус:** ✅ **Transcription Pipeline готов**
- Workflow: `GenomAI - Creative Transcription` (ID: `WMnFHqsFh8i7ddjV`) - активен

❗ **UPDATE транскрипта запрещён**

## 5. Decomposition & Canonical Schema ✅ COMPLETED
- [x] LLM decomposition workflow
- [x] Проверка schema_version
- [x] Запись в decomposed_creatives
- [x] Emit CreativeDecomposed

**Статус:** ✅ **Decomposition готов**
- Workflow: `creative_decomposition_llm` (ID: `mv6diVtqnuwr7qev`) - активен

## 6. Decision Engine (n8n + Render API) ✅ COMPLETED

### 6.1 Decision Workflow
- [x] Загрузка Idea + Learning Memory
- [x] Проверка confidence (death_memory check)
- [x] Проверка fatigue
- [x] Apply rules (4 checks: schema, death, fatigue, risk)
- [x] Emit DecisionMade

**Статус:** ✅ **Decision Engine готов**
- Workflow: `decision_engine_mvp` (ID: `YT2d7z5h9bPy1R4v`) - активен
- API: `genomai.onrender.com/api/decision/`

❗ **LLM здесь запрещён**

## 7. Hypothesis Factory (n8n + LLM) ✅ COMPLETED
- [x] Определение mutation scope
- [x] Формирование prompt
- [x] LLM generation (OpenAI)
- [x] Запись hypotheses
- [x] Emit HypothesisGenerated

**Статус:** ✅ **Hypothesis Factory готов**
- Workflow: `hypothesis_factory_generate` (ID: `oxG1DqxtkTGCqLZi`) - активен

## 8. Delivery (Telegram) ✅ COMPLETED
- [x] Отправка гипотезы байеру
- [x] Запись в deliveries
- [x] Emit HypothesisDelivered

**Статус:** ✅ **Telegram Delivery готов**
- Workflow: `Telegram Hypothesis Delivery` (ID: `5q3mshC9HRPpL6C0`) - активен

## 9. Metrics Ingestion (Keitaro) ✅ COMPLETED
- [x] Pull raw metrics по tracker_id
- [x] Запись в raw_metrics_current
- [x] Emit RawMetricsObserved

**Статус:** ✅ **Metrics Ingestion готов**
- Workflow: `Keitaro Poller` (ID: `0TrVJOtHiNEEAsTN`) - активен (schedule + webhook)

## 10. Daily Scan (Scheduler) ✅ COMPLETED
- [x] n8n cron (каждые 30 мин через Keitaro Poller)
- [x] Чтение raw metrics
- [x] Создание daily_metrics_snapshot
- [x] Emit DailyMetricsSnapshotCreated

**Статус:** ✅ **Daily Scan готов**
- Workflow: `Snapshot Creator` (ID: `Gii8l2XwnX43Wqr4`) - активен

❗ **Snapshot не обязателен**

## 11. Outcome Aggregation ✅ COMPLETED
- [x] Проверка наличия snapshot'ов
- [x] Закрытие окна (window_id)
- [x] Создание outcome_aggregates
- [x] Emit OutcomeAggregated

**Статус:** ✅ **Outcome Aggregation готов**
- Workflow: `Outcome Aggregator` (ID: `243QnGrUSDtXLjqU`) - активен
- Workflow: `Outcome Processor` (ID: `bbbQC4Aua5E3SYSK`) - активен

❗ **Без snapshot — abort**

## 12. Learning Loop ✅ COMPLETED
- [x] Проверка origin_type = system
- [x] Проверка неиспользованного outcome (learning_applied=false)
- [x] Update confidence (new version в idea_confidence_versions)
- [x] Update death_state при необходимости
- [x] Emit OutcomeAppliedToLearning

**Статус:** ✅ **Learning Loop готов**
- Workflow: `Learning Loop v2` (ID: `fzXkoG805jQZUR3S`) - активен
- API: `genomai.onrender.com/learning/process`

❗ **Строго один раз**

❌ **Manual re-run of learning steps is forbidden.**  
**Learning is event-driven only.**

## 13. Error Handling
- [ ] Abort при нарушении правил
- [ ] Нет retry learning
- [ ] Нет компенсации отсутствующих данных
- [ ] Логирование причины abort

## 14. Observability (MVP)
- [ ] Structured logs
- [ ] Correlation IDs
- [ ] Event count metrics
- [ ] Learning abort reasons

## 15. Manual Sanity Checks

**Перед первым реальным использованием:**
- [ ] Создать тестовый creative
- [ ] Прогнать через весь pipeline
- [ ] Проверить event log
- [ ] Проверить snapshot поведение
- [ ] Убедиться, что learning не происходит без outcome

## 16. Hard Invariants (нельзя нарушать)

❌ **Learning без Outcome**  
❌ **Decision через LLM**  
❌ **UPDATE immutable таблиц**  
❌ **Snapshot ≠ outcome**  
❌ **Outcome ≠ learning**
❌ **Manual re-run of learning steps** — Learning is event-driven only

## 17. MVP Done Criteria

MVP считается готовым, если:
- [ ] байер получает гипотезы в Telegram
- [ ] система собирает метрики
- [ ] daily snapshots создаются (если есть данные)
- [ ] outcomes формируются
- [ ] learning обновляется корректно
- [ ] ничего не ломается при отсутствии данных

## Финал

Если ты идёшь по этому чеклисту —
ты не "пишешь систему",
ты реализуешь зафиксированную архитектуру.
