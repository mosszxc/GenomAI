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

## 4. Transcription Pipeline
- [ ] Триггер транскрипции
- [ ] Получение результата
- [ ] Запись в transcripts (version = 1)
- [ ] Emit TranscriptCreated

❗ **UPDATE транскрипта запрещён**

## 5. Decomposition & Canonical Schema
- [ ] LLM decomposition workflow
- [ ] Проверка schema_version
- [ ] Запись в decomposed_creatives
- [ ] Emit CreativeDecomposed

## 6. Decision Engine (n8n)

### 6.1 Decision Workflow
- [ ] Загрузка Idea + Learning Memory
- [ ] Проверка confidence
- [ ] Проверка fatigue
- [ ] Apply rules
- [ ] Emit DecisionMade

❗ **LLM здесь запрещён**

## 7. Hypothesis Factory (n8n + LLM)
- [ ] Определение mutation scope
- [ ] Формирование prompt
- [ ] LLM generation
- [ ] Запись hypotheses
- [ ] Emit HypothesisGenerated

## 8. Delivery (Telegram)
- [ ] Отправка транскрипта байеру
- [ ] Запись в deliveries
- [ ] Emit HypothesisDelivered

## 9. Metrics Ingestion (Keitaro)
- [ ] Pull raw metrics по tracker_id
- [ ] Запись в raw_metrics_current
- [ ] Emit RawMetricsObserved

## 10. Daily Scan (Scheduler)
- [ ] n8n cron (1 раз в день)
- [ ] Чтение raw metrics
- [ ] Создание daily_metrics_snapshot
- [ ] Emit DailyMetricsSnapshotCreated

❗ **Snapshot не обязателен**

## 11. Outcome Aggregation
- [ ] Проверка наличия snapshot'ов
- [ ] Закрытие окна (например, D1–D3)
- [ ] Создание outcome_aggregates
- [ ] Emit OutcomeAggregated

❗ **Без snapshot — abort**

## 12. Learning Loop
- [ ] Проверка origin_type = system
- [ ] Проверка неиспользованного outcome
- [ ] Update confidence (new version)
- [ ] Update fatigue (new version)
- [ ] Emit OutcomeAppliedToLearning

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
