# 🧬 GenomAI

> Autonomous Creative Decision System — полностью автономная система принятия креативных решений в нестабильной рыночной среде

## 📖 О проекте

**GenomAI** — это автономная система принятия креативных решений, предназначенная для:
- **Обнаружения устойчивых связок** креативных переменных
- **Эволюции через контролируемые мутации** существующих паттернов
- **Управления выгоранием аудитории** на уровне кластеров
- **Системного повышения hitrate** решений во времени

GenomAI функционирует как внешний стратегический мозг, где:
- рынок является единственным источником истины
- решения оцениваются по последствиям
- обучение происходит на результатах собственных действий

### 🎯 Основные принципы

1. **Market is the only ground truth**
2. **Survival > short-term revenue**
3. **Decision → Outcome → Learning**
4. **Selection bias признаётся и не «лечится»**
5. **Выгорание — сигнал, а не ошибка**
6. **Автоматизация предпочтительнее ручных решений**
7. **Человек — interrupt, а не участник цикла**

### 🧠 Архитектура принятия решений

```
External Signals (Market / Spy / Context)
            ↓
ML Advisory Layer
(similarity, novelty, fatigue signals)
            ↓
ML → Bucket Conversion
(float → discrete buckets)
            ↓
Decision Engine
(rules, policies, constraints)
            ↓
Hypothesis Factory
            ↓
Market Execution
            ↓
Outcome Logging
            ↓
Learning Loop
            ↓
Decision Engine
```

**ML никогда не bypass'ит Decision Engine.**  
**Decision Engine работает ТОЛЬКО с bucket-значениями, не с raw float.**

---

## 📚 Документация

### 🟥 Layer 0 — Doctrine / Конституция системы

**Высший приоритет.** Фундаментальные принципы, правила и политики системы.

📘 **[Concept Document](./docs/layer-0-doctrine/CONCEPT.md)** — Концептуальный документ проекта (v1.0):
- Краткое определение системы
- Цели проекта (продуктовая, операционная, стратегическая)
- Базовые принципы и инварианты
- Доменная модель и основные сущности
- Язык системы (Canonical Schema)
- 14 процессов системы (сквозной жизненный цикл)
- Память и обучение
- Роль ИИ и автоматизации
- Типичные риски и ловушки
- **Начните с этого документа для общего понимания**

🔒 **[Architecture Lock / Doctrine](./docs/layer-0-doctrine/ARCHITECTURE_LOCK.md)** — Высший архитектурный артефакт проекта (v1.0):
- Архитектурные инварианты и запреты
- Роли компонентов системы (Decision Engine, ML, LLM, n8n, Human)
- **Критическое правило дискретизации ML-сигналов:** Decision Engine получает ТОЛЬКО buckets, не raw float
- Non-negotiable правила и границы автоматизации
- **Этот документ выше PRD, задач и спринтов**

📋 **[Development Order](./docs/DEVELOPMENT_ORDER.md)** — Строгий порядок разработки системы (engineering roadmap):
- 18 фаз разработки от архитектурного lock до human override layer
- Правило: любой этап нельзя начинать, если предыдущий не зафиксирован документально

📚 **[Domain Model / Glossary](./docs/layer-1-logic/DOMAIN_MODEL.md)** — Единый словарь предметной области (v1.0):
- Определение ключевых сущностей (Idea, Hypothesis, Creative, Outcome, Decision и др.)
- Запрещённые смешения понятий
- **Если термин не определён здесь — он не используется в системе**

### 🟧 Layer 1 — System Design / Logical Architecture

**Логическая архитектура системы.** Спецификации компонентов, схемы данных, контракты.

📐 **[Canonical Schema Specification](./docs/layer-1-logic/CANONICAL_SCHEMA.md)** — Каноническая схема данных (v1.2):
- Строгая типизация всех сущностей (Idea, Hypothesis, Outcome, Decision)
- Enum определения для всех полей
- State Transition (state_before → state_after) — core-поля Idea
- Cultural Context (context_frame) — core-поле Idea
- Narrative Tension (tension_type) — derived/advisory signal
- ML signal buckets (novelty_bucket, similarity_bucket, confidence_bucket) — дискретизация для Decision Engine
- Historical cluster tracking (active_cluster_id, cluster_at_decision, cluster_id_at_outcome)
- Policy versioning (policy_version в Decision)
- Правила валидации и версионирования
- **Если поля нет в schema — его не существует**

⚙️ **[Decision Engine Specification](./docs/layer-1-logic/DECISION_ENGINE.md)** — Детерминированное ядро системы (v1.1):
- Единственный компонент, принимающий решения (APPROVE/REJECT/DEFER)
- Фиксированный порядок проверок (9 checks)
- **ML signal discretization:** работает ТОЛЬКО с bucket-значениями, не с raw float
- Использование State Transition, Narrative Tension, Cultural Context
- Обязательный decision trace с минимальным explainability contract (6–7 полей)
- **Decision Engine использует только значения полей, никогда не использует интерпретации/объяснения**
- **Decision Engine — закон системы**

🔒 **[Data Contracts Specification](./docs/layer-1-logic/DATA_CONTRACTS.md)** — Контракты входных данных (v1.0):
- Контракты для всех источников данных (performance, spy, LLM, human override)
- Правила валидации и отклонения невалидных данных
- Запрет silent correction и coercion
- **Data contracts — иммунная система GenomAI**

🔄 **[Data Flow Specification](./docs/layer-1-logic/DATA_FLOW.md)** — Канонический поток данных и жизненный цикл объектов (v1.0):
- Логический путь данных от входа до обучения
- Порядок обработки: Input → Validation → Decomposition → Idea Registration → Decision Engine → Hypothesis Generation → Execution → Outcome Ingestion → Learning Loop
- Временные гарантии и fail-safe стратегии
- **Ни один объект не может появиться без причины, ни одно обучение без решения**

🔁 **[Entity Lifecycle Specification](./docs/layer-1-logic/ENTITY_LIFECYCLE.md)** — Жизненный цикл и владение сущностями (v1.0):
- Правила создания, изменения и закрытия всех сущностей (Creative, Idea, Hypothesis, Decision, Outcome, Cluster, Memory)
- Ownership Matrix — кто владеет каждой сущностью
- Запрещённые операции и cross-entity гарантии
- **Сущности отражают реальность системы, а не желания человека. Система не переписывает историю**

🏗️ **[System Architecture Specification](./docs/layer-1-logic/SYSTEM_ARCHITECTURE.md)** — Логическая архитектура системы (v1.0):
- Компоненты системы и их ответственность (Ingestion, Validation, Decomposition, Idea Registry, Decision Engine, Hypothesis Factory, Outcome Ingestion, Learning Loop, Memory Stores)
- Allowed Interactions Matrix — разрешённые взаимодействия между компонентами
- Forbidden Interactions — запрещённые связи
- Sync/Async семантика и failure isolation
- **Компоненты не думают. Думает только система в целом. Решает только Decision Engine**

🤖 **[LLM Usage Policy](./docs/layer-1-logic/LLM_USAGE_POLICY.md)** — Политика использования LLM (v1.0):
- Разрешенные use cases (decomposition, classification, hypothesis generation)
- Запрещенные use cases (decision-making, risk assessment, schema modification)
- Правила валидации и изоляции LLM от decision logic
- **LLMs — ускорители, а не авторитеты**

🧠 **[Learning & Memory Policy](./docs/layer-1-logic/LEARNING_MEMORY_POLICY.md)** — Политика обучения и памяти (v1.2):
- Типы памяти (Outcome, Decision, Death, Fatigue, Confidence)
- Time Decay Policy — устаревание знаний (~30 дней базовый срок)
- Горизонты обучения (T1, T2, T3) с изоляцией (cross-horizon leakage prevention)
- Learning Loop механизм
- Fatigue на уровнях: skin, message, angle, transition, tension, context, exhausted
- **Tension fatigue ≠ idea death** — форма конфликта может выгореть, но идея остаётся живой
- Epistemic Shock rate limiting (максимальная частота, cooldown, бюджет)
- Historical vs Active cluster tracking (нет ретроактивного переписывания истории)
- **Система помнит ошибки дольше, чем успехи**

👤 **[Usage & Interaction Doctrine](./docs/layer-0-doctrine/USAGE_DOCTRINE.md)** — Модель взаимодействия медиабайера с системой (v1.1):
- Push-модель взаимодействия (без интерактивных запросов)
- Telegram Bot как транспортный интерфейс (не логический компонент)
- Core Usage Loop: загрузка транскриптов → запуск → передача фактов → получение решений
- Feedback Contract: только факты, без интерпретаций
- Запрещённое использование (blacklist): чат, копирайтер, ручной выбор идей
- Responsibility Split: кто за что отвечает
- **Медиабайер кормит систему фактами, система возвращает решения и допустимые реализации**

### 🟨 Layer 2 — Product & Integration Specs

**Спецификации продукта и интеграций.** API, интерфейсы, интеграционные контракты.

💬 **[Telegram Interaction Model Specification](./docs/layer-2-product/TELEGRAM_INTERACTION_MODEL.md)** — Модель взаимодействия через Telegram-бота (v1.0):
- Push-Only Model — строго событийная коммуникация, запросно-ответная модель запрещена
- Типы сообщений: Creative Transcript, Performance Outcome, Decision Result, Generated Transcript, System Notification
- Stateless Messaging — каждое сообщение изолировано, состояние только внутри системы
- **Критическое ограничение:** пользователь передаёт только транскрипты видео, не визуалы/primary/description
- Forbidden Interaction Patterns: диалог, команды, выбор идей, ручной триггер Decision Engine
- **Telegram — транспорт, а не мозг. Если Telegram начинает управлять системой — архитектура нарушена**

📥 **[Input Normalization Specification](./docs/layer-2-product/INPUT_NORMALIZATION.md)** — Правила нормализации и приёма входных данных (v1.0):
- Поддерживаемые типы входов: Creative Video Reference (video_url + tracker_id), Performance Outcome Reference
- Автоматическая транскрипция — Media Buyer никогда не присылает транскрипт вручную
- **Критическое ограничение:** система работает ТОЛЬКО с транскриптом видео (аудиочасть)
- Нормализация: проверка доступности видео → проверка tracker_id → создание Creative → транскрипция → валидация
- Forbidden Input Patterns: ручной транскрипт, частичный текст, Creative без tracker_id
- **Media Buyer передаёт ссылки и факты. Система берёт на себя всё остальное**

📤 **[Output Payloads Specification](./docs/layer-2-product/OUTPUT_PAYLOADS.md)** — Выходные данные системы (v1.0):
- Поддерживаемые типы выходов: Decision Result, Generated Transcript, Constraint Notice, Outcome Acknowledgement, Error/Rejection
- **Критическое ограничение:** транскрипты содержат ТОЛЬКО текст речи, не визуалы/primary/description
- Forbidden Output Types: ранжирование, рекомендации, прогнозы, внутренние метрики, варианты «на выбор»
- Silent Output Semantics: молчание — валидный output
- **Система говорит ровно столько, сколько нужно для действия — и ни словом больше**

🔄 **[User Flows Specification](./docs/layer-2-product/USER_FLOWS.md)** — Канонические пользовательские сценарии (v1.1):
- 8 основных флоу: Creative Registration, Transcription Failure, Receiving New Test Transcripts, External Launch, Performance Feedback Submission, Re-evaluation, Deferred/Rejected Idea, Silent Operation Mode
- Автоматическая транскрипция — пользователь никогда не видит и не редактирует транскрипт
- **Критическое ограничение:** система работает ТОЛЬКО с транскриптом видео (аудиочасть)
- Асинхронность: один вход → 0..N выходов, порядок сообщений не гарантирован
- Forbidden User Flows: ручная отправка транскриптов, редактирование текста, запросы генерации, выбор идей
- **Пользователь взаимодействует с системой через ссылки и факты, все смысловые преобразования — внутреннее дело GenomAI**

🎯 **[MVP Scope Specification](./docs/layer-2-product/MVP_SCOPE.md)** — Минимальный жизнеспособный продукт (v1.0):
- In-Scope: video_url + tracker_id, автоматическая транскрипция, Decision Engine (MVP Mode), базовый Learning Loop, Telegram (push-модель)
- Out-of-Scope: epistemic shock, multi-horizon logic, advanced ML signals, human override, scaling, analytics
- MVP Success Criteria: корректная работа системы, получение Outcome, изменение поведения от обучения
- Exit Criteria: накопление N Outcome, система убила идею/сменила поведение/перестала выдавать из-за fatigue
- **MVP не меняет архитектуру, временно отключает часть возможностей. Если функция не обоснована получением Outcome — она лишняя**

### 🟩 Layer 3 — Implementation & Infra

**Спецификации реализации и инфраструктуры.** Логические сервисы, технологии, деплой.

🔧 **[Service Boundaries Specification](./docs/layer-3-implementation-design/SERVICE_BOUNDARIES.md)** — Границы сервисов и ответственность (v1.0):
- 10 логических сервисов: Ingestion, Validation, Transcription, Decomposition, Idea Registry, Decision Engine, Hypothesis Factory, Outcome Ingestion, Learning Loop, Memory Store
- Stateless vs Stateful сервисы и их различия
- Allowed Service Interactions — разрешённые взаимодействия между сервисами
- Forbidden Couplings — запрещённые связи (Decision Engine ↔ Memory Store write, Decomposition ↔ Outcome и др.)
- **Сервис знает только то, что ему архитектурно разрешено знать. Если сервис знает больше — он спроектирован неверно**

💾 **[Storage Model Specification](./docs/layer-3-implementation-design/STORAGE_MODEL.md)** — Каноническая модель хранения данных (v1.0):
- 4 логических слоя хранения: Raw Input (mutable), Temporal Snapshots (immutable), Aggregated Outcomes (immutable), Learning Memory (append-only)
- Daily Scan как механизм создания Temporal Snapshots (DailyMetricsSnapshot)
- Outcome как агрегированное окно (OutcomeAggregate), не равное raw metrics или daily snapshot
- Правила immutability: если данные можно изменить — на них нельзя обучаться
- Learning Memory обновляется ТОЛЬКО на основе OutcomeAggregate с origin_type = system
- **Система никогда не обучается на "сырых" данных. Обучение возможно только на агрегированных, временнó стабилизированных outcome**

📅 **[Event Model Specification](./docs/layer-3-implementation-design/EVENT_MODEL.md)** — Каноническая модель событий (v1.1):
- 5 классов событий: Ingestion Events, Metric Observation Events, Temporal Aggregation Events, Decision & Execution Events, Learning Events
- Canonical Event Flow: CreativeReferenceReceived → RawMetricsObserved → DailyMetricsSnapshotCreated → OutcomeWindowClosed → OutcomeAggregated → OutcomeAppliedToLearning
- Критическое правило: Learning возможен только после закрытия окна и агрегации
- Запрещённые паттерны: Learning на RawMetricsObserved, Learning на DailyMetricsSnapshotCreated, Decision на основе snapshot или raw
- **Если событие отражает "прямо сейчас", оно не может влиять на будущее решений**

⚠️ **[Error Handling Specification](./docs/layer-3-implementation-design/ERROR_HANDLING.md)** — Семантика обработки ошибок и сбоев (v1.0):
- 5 классов ошибок: Data Absence, Data Delay, Data Duplication, Processing Failure, Semantic Violation
- Правила обработки по слоям (L1-L4): Raw Metrics, Daily Snapshot, Outcome Aggregation, Learning
- Retry/No-Retry Matrix: retry только для ingestion и snapshot creation, запрет retry для aggregation и learning
- Idempotency Enforcement: повтор OutcomeAppliedToLearning = hard abort
- Partial Failure Semantics: никакой rollback истории не допускается
- Silent Failure Rule: система не обязана объяснять пользователю причины
- **Лучше не обучиться, чем обучиться неправильно. Никакая ошибка не имеет права изменить знания системы**

---

## 📁 Структура проекта

```
.
├── docs/                              # 📚 Документация
│   ├── DEVELOPMENT_ORDER.md           # Порядок разработки системы
│   ├── README.md                      # Обзор документации
│   ├── layer-0-doctrine/              # 🟥 Doctrine / Конституция системы
│   │   ├── README.md
│   │   ├── ARCHITECTURE_LOCK.md
│   │   ├── CONCEPT.md
│   │   └── USAGE_DOCTRINE.md
│   ├── layer-1-logic/                 # 🟧 System Design / Logical Architecture
│   │   ├── README.md
│   │   ├── SYSTEM_ARCHITECTURE.md
│   │   ├── DOMAIN_MODEL.md
│   │   ├── ENTITY_LIFECYCLE.md
│   │   ├── CANONICAL_SCHEMA.md
│   │   ├── DATA_FLOW.md
│   │   ├── DECISION_ENGINE.md
│   │   ├── LEARNING_MEMORY_POLICY.md
│   │   ├── DATA_CONTRACTS.md
│   │   ├── LLM_USAGE_POLICY.md
│   │   └── ENVIRONMENT_CONTEXT.md
│   ├── layer-2-product/               # 🟨 Product & Integration Specs
│   │   ├── README.md
│   │   ├── USER_FLOWS.md
│   │   ├── TELEGRAM_INTERACTION_MODEL.md
│   │   ├── INPUT_NORMALIZATION.md
│   │   ├── OUTPUT_PAYLOADS.md
│   │   └── MVP_SCOPE.md
│   ├── layer-3-implementation-design/ # 🟩 Implementation Design
│   │   ├── README.md
│   │   ├── SERVICE_BOUNDARIES.md
│   │   ├── EVENT_MODEL.md
│   │   ├── STORAGE_MODEL.md
│   │   └── ERROR_HANDLING.md
│   └── layer-4-implementation-planning/ # 🟦 Implementation Planning
│       ├── README.md
│       ├── TECH_DECISIONS.md
│       ├── DATA_SCHEMAS.md
│       ├── API_CONTRACTS.md
│       └── IMPLEMENTATION_CHECKLIST.md
├── .github/                 # ⚙️ GitHub настройки
│   ├── workflows/          # GitHub Actions
│   ├── ISSUE_TEMPLATE.md   # Шаблон для создания Issues
│   └── PULL_REQUEST_TEMPLATE.md # Шаблон для создания PR
├── .gitignore              # Игнорируемые файлы
└── README.md               # 📖 Этот файл
```

---

## 🎯 Статус проекта

**🟥 Layer 0 — Doctrine:**
- ✅ **Concept Document** - [Concept Document](./docs/layer-0-doctrine/CONCEPT.md) (v1.0)
- ✅ **Architecture Lock** - [Architecture Lock / Doctrine](./docs/layer-0-doctrine/ARCHITECTURE_LOCK.md) (v1.0)
- ✅ **Usage & Interaction Doctrine** - [Usage & Interaction Doctrine](./docs/layer-0-doctrine/USAGE_DOCTRINE.md) (v1.1)

**🟧 Layer 1 — System Design:**
- ✅ **System Architecture** - [System Architecture Specification](./docs/layer-1-logic/SYSTEM_ARCHITECTURE.md) (v1.0)
- ✅ **Domain Model** - [Domain Model / Glossary](./docs/layer-1-logic/DOMAIN_MODEL.md) (v1.0)
- ✅ **Entity Lifecycle** - [Entity Lifecycle Specification](./docs/layer-1-logic/ENTITY_LIFECYCLE.md) (v1.0)
- ✅ **Canonical Schema** - [Canonical Schema Specification](./docs/layer-1-logic/CANONICAL_SCHEMA.md) (v1.2)
- ✅ **Data Flow** - [Data Flow Specification](./docs/layer-1-logic/DATA_FLOW.md) (v1.0)
- ✅ **Decision Engine** - [Decision Engine Specification](./docs/layer-1-logic/DECISION_ENGINE.md) (v1.1)
- ✅ **Learning & Memory Policy** - [Learning & Memory Policy](./docs/layer-1-logic/LEARNING_MEMORY_POLICY.md) (v1.2)
- ✅ **Data Contracts** - [Data Contracts Specification](./docs/layer-1-logic/DATA_CONTRACTS.md) (v1.0)
- ✅ **LLM Usage Policy** - [LLM Usage Policy](./docs/layer-1-logic/LLM_USAGE_POLICY.md) (v1.0)
- ✅ **Environment Context** - [Environment Context Specification](./docs/layer-1-logic/ENVIRONMENT_CONTEXT.md) (v1.0)

**🟨 Layer 2 — Product & Integration:**
- ✅ **User Flows** - [User Flows Specification](./docs/layer-2-product/USER_FLOWS.md) (v1.1)
- ✅ **Telegram Interaction Model** - [Telegram Interaction Model Specification](./docs/layer-2-product/TELEGRAM_INTERACTION_MODEL.md) (v1.0)
- ✅ **Input Normalization** - [Input Normalization Specification](./docs/layer-2-product/INPUT_NORMALIZATION.md) (v1.0)
- ✅ **Output Payloads** - [Output Payloads Specification](./docs/layer-2-product/OUTPUT_PAYLOADS.md) (v1.0)
- ✅ **MVP Scope** - [MVP Scope Specification](./docs/layer-2-product/MVP_SCOPE.md) (v1.0)

**🟩 Layer 3 — Implementation Design:**
- ✅ **Service Boundaries** - [Service Boundaries Specification](./docs/layer-3-implementation-design/SERVICE_BOUNDARIES.md) (v1.0)
- ✅ **Event Model** - [Event Model Specification](./docs/layer-3-implementation-design/EVENT_MODEL.md) (v1.1)
- ✅ **Storage Model** - [Storage Model Specification](./docs/layer-3-implementation-design/STORAGE_MODEL.md) (v1.0)
- ✅ **Error Handling** - [Error Handling Specification](./docs/layer-3-implementation-design/ERROR_HANDLING.md) (v1.0)

**🟦 Layer 4 — Implementation Planning:**
- 🚧 **Technical Decisions** - [Technical Decisions](./docs/layer-4-implementation-planning/TECH_DECISIONS.md) (v1.0, в разработке)
- 🚧 **Data Schemas** - [Data Schemas](./docs/layer-4-implementation-planning/DATA_SCHEMAS.md) (v1.0, в разработке)
- 🚧 **API Contracts** - [API Contracts](./docs/layer-4-implementation-planning/API_CONTRACTS.md) (v1.0, в разработке)
- 🚧 **Implementation Checklist** - [Implementation Checklist](./docs/layer-4-implementation-planning/IMPLEMENTATION_CHECKLIST.md) (v1.0, в разработке)
- ✅ **Порядок разработки** - [Development Order](./docs/DEVELOPMENT_ORDER.md)
- ✅ **GitHub репозиторий** - настроен и готов к работе
- 🚧 **Разработка** - в процессе

---

## 💡 Ключевые концепции

### Decision Horizon Doctrine

Система работает с тремя временными горизонтами:
- **T₁ (0–3 дня)**: первичная реакция рынка, exploration
- **T₂ (3–14 дней)**: устойчивость и повторяемость, основной рабочий горизонт
- **T₃ (14+ дней)**: обновление политик и ограничений

**Cross-horizon leakage prevention:** сигналы из T1 НЕ обновляют стратегические priors (T3).

### Hypothesis Death & Resurrection

Система различает три состояния гипотез:
- **Soft Failure**: единичный провал, гипотеза доступна с отрицательным весом
- **Hard Failure**: повторяемый провал, exploit запрещён
- **Dead Hypothesis**: полностью исключается из генерации, логируется в Death Memory

### Fatigue Doctrine

Выгорание детектируется на уровне кластеров:
1. **Skin Exhaustion** → только визуальные мутации
2. **Message Exhaustion** → запрет повторения message-структур
3. **Angle Exhaustion** → exploit полностью запрещён
4. **Transition Exhaustion** → усталость от повторяющегося перехода состояния
5. **Tension Exhaustion** → усталость от одинаковой формы конфликта (≠ idea death)
6. **Context Exhaustion** → усталость от рамки доверия
7. **Forced Novelty** → принудительное exploration

### ML Signal Discretization

**Критическое правило:** Decision Engine работает ТОЛЬКО с bucket-значениями, не с raw float.

- ML предоставляет: `similarity_score`, `novelty_score`, `confidence_weight` (float)
- Decision Engine получает: `similarity_bucket`, `novelty_bucket`, `confidence_bucket` (enum)
- Конвертация float → bucket явная, версионированная, воспроизводимая

**Результат:** Decision Engine остаётся детерминированным и explainable. ML полностью advisory.

### Epistemic Shock Rate Limiting

**Правила:**
- Максимальная частота: не чаще 1 shock на N решений (например, 1 на 50–100)
- Минимальный cooldown: обязательный интервал между shock (например, 24 часа)
- Бюджет: выделенный бюджет (например, не более 5–10% от общего)

**Результат:** Shock остаётся инструментом, а не режимом. Система не «дергается».

### Historical vs Active Cluster Tracking

- `active_cluster_id` в Idea — текущее состояние (может меняться)
- `cluster_at_decision` в Decision — исторический снимок
- `cluster_id_at_outcome` в Outcome — исторический снимок

**Результат:** Нет ретроактивного «переписывания истории». Learning Loop корректный во времени.

### State Transition, Narrative Tension, Cultural Context

**State Transition** (state_before → state_after) — что продаётся  
**Narrative Tension** (tension_type) — почему человек не может остаться прежним  
**Cultural Context** (context_frame) — почему он вообще слушает  

Это механизмы контроля причин, без которых система видит только следствия и не управляет деградацией.

---

## 🎯 Финальный принцип

Идеальная GenomAI — это система, которая зарабатывает, когда человек ей не мешает.

Человек остаётся источником редкого сдвига.

Все остальные решения — ответственность системы.

---

## ❓ Нужна помощь?

Если что-то непонятно:
1. Начните с [Concept Document](./docs/layer-0-doctrine/CONCEPT.md) — общее понимание системы
2. Изучите [Architecture Lock](./docs/layer-0-doctrine/ARCHITECTURE_LOCK.md) — это основа всех решений
3. Изучите [Domain Model](./docs/layer-1-logic/DOMAIN_MODEL.md) — единый язык системы
4. Ознакомьтесь с [Canonical Schema](./docs/layer-1-logic/CANONICAL_SCHEMA.md) — структура данных
5. Изучите [Data Contracts](./docs/layer-1-logic/DATA_CONTRACTS.md) — контракты входных данных
6. Прочитайте [LLM Usage Policy](./docs/layer-1-logic/LLM_USAGE_POLICY.md) — правила использования LLM
7. Изучите [Learning & Memory Policy](./docs/layer-1-logic/LEARNING_MEMORY_POLICY.md) — обучение и память системы
8. Прочитайте [Decision Engine Specification](./docs/layer-1-logic/DECISION_ENGINE.md) — ядро системы
9. Изучите [Usage & Interaction Doctrine](./docs/layer-0-doctrine/USAGE_DOCTRINE.md) — как медиабайер взаимодействует с системой
10. Следуйте [Development Order](./docs/DEVELOPMENT_ORDER.md) для разработки
11. Спросите у меня (AI помощника) - я помогу!

---

**Удачи в разработке! 🎉**
