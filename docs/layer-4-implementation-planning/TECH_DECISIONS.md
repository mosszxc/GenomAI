# GenomAI — Technology Decisions & Stack Freeze (Layer 4)
Версия: v1.3
Статус: IMPLEMENTATION PLANNING / LAYER 4
Приоритет: Критический
Scope: MVP
Основан на: SERVICE_BOUNDARIES, EVENT_MODEL v1.1, STORAGE_MODEL, ERROR_HANDLING

## ⚠️ Изменения в v1.3

**Decision Engine мигрирован на Render:**
- Decision Engine теперь реализован как REST API сервис на Render
- n8n workflow вызывает Render API вместо локальной логики
- Сохранены все архитектурные принципы (детерминированность, stateless)
- См. `DECISION_ENGINE_RENDER_MIGRATION.md` для деталей миграции

## 1. Purpose

Данный документ фиксирует технологический контур реализации MVP,
чтобы:
- исключить пересборку стека «по дороге»,
- предотвратить архитектурный дрейф,
- сделать реализацию механическим исполнением Layer 3.

Документ НЕ обсуждает альтернативы и НЕ сравнивает технологии.

## 2. Stack Freeze (ключевое решение)

Проект реализуется строго поверх существующего стека команды.

Выбор базовых технологий:
- ❌ не обсуждается
- ❌ не пересматривается в рамках MVP
- ✅ считается зафиксированным

Любое изменение стека допускается только после MVP
через новую версию этого документа.

## 3. Authoritative Stack

### 3.1 Data Platform

**Supabase**
- PostgreSQL — единственный source of truth
- используется для:
  - event log
  - snapshots
  - outcome aggregates
  - learning memory
- Supabase Auth / Storage — вне scope MVP

### 3.2 Orchestration & Execution

**n8n**
- основной execution engine системы
- оркестрация всех workflow
- реализация:
  - ingestion
  - hypothesis generation
  - daily scan
  - learning loop
- n8n рассматривается как:
  - детерминированный workflow-движок,
  - а не как источник интеллекта

**Render (Decision Engine Service)**
- REST API сервис для Decision Engine
- реализация:
  - детерминированная логика принятия решений
  - проверки допустимости идей
  - формирование Decision Trace
- сервис stateless, детерминированный
- n8n вызывает Render API для принятия решений

### 3.3 Tracking & Performance

**Keitaro**
- единственный источник performance-метрик
- pull-based чтение
- идентификация по tracker_id

### 3.4 Traffic Source

**Facebook Ads**
- источник трафика
- нет прямой интеграции с FB API в MVP
- все данные поступают только через Keitaro

### 3.5 User Interface

**Telegram Bot**
- единственный UI в MVP
- приём:
  - video_url
  - tracker_id
- выдача:
  - гипотез (транскриптов)
  - статусов обработки

## 4. Architectural Mapping (Layer 3 → Stack)

### 4.1 Logical Services → Реализация

| Logical Service | Реализация |
|----------------|------------|
| Ingestion Service | n8n webhook workflow |
| Validation Service | n8n validation nodes |
| Transcription Service | существующий внешний workflow |
| Decomposition Service | n8n + LLM call |
| Idea Registry | Supabase (Postgres) |
| Decision Engine | Render REST API service (deterministic) |
| Hypothesis Factory | n8n workflow + LLM |
| Outcome Ingestion | n8n pull from Keitaro |
| Metrics Scanner | n8n scheduled workflow |
| Learning Loop | n8n workflow (rules-based) |
| Memory Store | Supabase (append-only tables) |

## 5. Decision Engine — Execution Rules

**Ключевое решение**

Decision Engine реализуется как REST API сервис на Render (Node.js/Express).

**Архитектура:**
- Stateless сервис (не хранит состояние между вызовами)
- Детерминированный (одинаковый input → одинаковый output)
- Все требуемое состояние загружается из Supabase при каждом вызове
- n8n workflow вызывает Render API через HTTP Request

**Допустимо**
- Детерминированные правила (IF / ELSE / SWITCH)
- Числовые пороги
- Чтение структурированных данных из Supabase
- Запись Decision и Decision Trace в Supabase
- Unit-тесты и integration-тесты

**Запрещено**
- Использование LLM
- Принятие решений на основе текста
- Implicit logic в промптах
- Обучение внутри decision-service
- Кеширование состояния между вызовами
- Глобальные переменные или shared state

**API Endpoint:**
- `POST /api/decision` — основной endpoint для принятия решений
- `GET /health` — health check endpoint

**Decision Engine:**
- воспроизводим
- тестируем
- аудитируем
- версионируем (код в Git)

**См. также:**
- `DECISION_ENGINE_RENDER_MIGRATION.md` — детали миграции
- `04_decision_engine_playbook.md` — playbook реализации

## 6. Hypothesis Factory — Execution Rules

**Ключевое решение**

Hypothesis Factory реализуется как n8n workflow
с использованием LLM исключительно для генерации текста.

**Разделение ответственности**

**n8n:**
- определяет mutation scope
- формирует prompt
- контролирует версии

**LLM:**
- только генерирует текст
- не знает о confidence / fatigue / outcome

**Обязательное логирование**
- prompt version
- input hash
- LLM output
- timestamp

## 7. Event Model Implementation

EVENT_MODEL.md реализуется через:
- append-only таблицу event_log в Supabase
- n8n workflows как producers / consumers

**Правила**
- никакие события не удаляются
- события не используются как команды
- OutcomeAppliedToLearning — строго один раз

## 8. Daily Scan & Metrics

**Ключевое решение**

Daily scan реализуется как n8n scheduled workflow (1 раз в сутки).

**Pipeline:**
1. Pull raw metrics из Keitaro
2. Запись raw metrics (mutable)
3. Создание DailyMetricsSnapshot (immutable)
4. Генерация события DailyMetricsSnapshotCreated

**Learning НЕ реагирует на:**
- raw metrics
- одиночные snapshot'ы

## 9. Data Handling Rules

- raw metrics → mutable
- daily snapshots → append-only
- outcome aggregates → immutable
- learning memory → versioned, append-only

Любое нарушение = архитектурная ошибка.

## 10. Non-Goals (жёстко)

В MVP запрещено:
- message brokers (Kafka / Rabbit)
- микросервисы (кроме Decision Engine на Render)
- realtime decisioning
- прямые интеграции с FB API
- ML pipelines / embeddings
- сложные дашборды

**Исключение:**
- Decision Engine на Render — разрешено для улучшения тестируемости и производительности

## 11. Operational Principles

- задержки данных допустимы
- отсутствие данных — валидное состояние
- learning может не происходить
- стабильность > полнота

## 12. Decision Freeze

Все решения выше:
- зафиксированы для MVP
- не пересматриваются «по ходу»
- изменяются только через новую версию этого документа

## Architectural Summary

- n8n = execution layer (оркестрация)
- Render = Decision Engine service (принятие решений)
- Supabase = memory & truth
- Keitaro = единственный performance source
- LLM = генератор, не мозг
- Decision = правила (на Render)
- Learning = агрегаты + окна
