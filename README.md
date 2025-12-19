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

📘 **[Concept Document](./docs/layer-0/CONCEPT.md)** — Концептуальный документ проекта (v1.0):
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

🔒 **[Architecture Lock / Doctrine](./docs/layer-0/ARCHITECTURE_LOCK.md)** — Высший архитектурный артефакт проекта (v1.0):
- Архитектурные инварианты и запреты
- Роли компонентов системы (Decision Engine, ML, LLM, n8n, Human)
- **Критическое правило дискретизации ML-сигналов:** Decision Engine получает ТОЛЬКО buckets, не raw float
- Non-negotiable правила и границы автоматизации
- **Этот документ выше PRD, задач и спринтов**

📋 **[Development Order](./docs/DEVELOPMENT_ORDER.md)** — Строгий порядок разработки системы (engineering roadmap):
- 18 фаз разработки от архитектурного lock до human override layer
- Правило: любой этап нельзя начинать, если предыдущий не зафиксирован документально

📚 **[Domain Model / Glossary](./docs/layer-0/DOMAIN_MODEL.md)** — Единый словарь предметной области (v1.0):
- Определение ключевых сущностей (Idea, Hypothesis, Creative, Outcome, Decision и др.)
- Запрещённые смешения понятий
- **Если термин не определён здесь — он не используется в системе**

### 🟧 Layer 1 — System Design / Logical Architecture

**Логическая архитектура системы.** Спецификации компонентов, схемы данных, контракты.

📐 **[Canonical Schema Specification](./docs/layer-1/CANONICAL_SCHEMA.md)** — Каноническая схема данных (v1.2):
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

⚙️ **[Decision Engine Specification](./docs/layer-1/DECISION_ENGINE.md)** — Детерминированное ядро системы (v1.1):
- Единственный компонент, принимающий решения (APPROVE/REJECT/DEFER)
- Фиксированный порядок проверок (9 checks)
- **ML signal discretization:** работает ТОЛЬКО с bucket-значениями, не с raw float
- Использование State Transition, Narrative Tension, Cultural Context
- Обязательный decision trace с минимальным explainability contract (6–7 полей)
- **Decision Engine использует только значения полей, никогда не использует интерпретации/объяснения**
- **Decision Engine — закон системы**

🔒 **[Data Contracts Specification](./docs/layer-1/DATA_CONTRACTS.md)** — Контракты входных данных (v1.0):
- Контракты для всех источников данных (performance, spy, LLM, human override)
- Правила валидации и отклонения невалидных данных
- Запрет silent correction и coercion
- **Data contracts — иммунная система GenomAI**

🤖 **[LLM Usage Policy](./docs/layer-0/LLM_USAGE_POLICY.md)** — Политика использования LLM (v1.0):
- Разрешенные use cases (decomposition, classification, hypothesis generation)
- Запрещенные use cases (decision-making, risk assessment, schema modification)
- Правила валидации и изоляции LLM от decision logic
- **LLMs — ускорители, а не авторитеты**

🧠 **[Learning & Memory Policy](./docs/layer-0/LEARNING_MEMORY_POLICY.md)** — Политика обучения и памяти (v1.2):
- Типы памяти (Outcome, Decision, Death, Fatigue, Confidence)
- Time Decay Policy — устаревание знаний (~30 дней базовый срок)
- Горизонты обучения (T1, T2, T3) с изоляцией (cross-horizon leakage prevention)
- Learning Loop механизм
- Fatigue на уровнях: skin, message, angle, transition, tension, context, exhausted
- **Tension fatigue ≠ idea death** — форма конфликта может выгореть, но идея остаётся живой
- Epistemic Shock rate limiting (максимальная частота, cooldown, бюджет)
- Historical vs Active cluster tracking (нет ретроактивного переписывания истории)
- **Система помнит ошибки дольше, чем успехи**

👤 **[Usage & Interaction Doctrine](./docs/layer-0/USAGE_DOCTRINE.md)** — Модель взаимодействия медиабайера с системой (v1.1):
- Push-модель взаимодействия (без интерактивных запросов)
- Telegram Bot как транспортный интерфейс (не логический компонент)
- Core Usage Loop: загрузка транскриптов → запуск → передача фактов → получение решений
- Feedback Contract: только факты, без интерпретаций
- Запрещённое использование (blacklist): чат, копирайтер, ручной выбор идей
- Responsibility Split: кто за что отвечает
- **Медиабайер кормит систему фактами, система возвращает решения и допустимые реализации**

---

## 📁 Структура проекта

```
.
├── docs/                    # 📚 Документация
│   ├── DEVELOPMENT_ORDER.md # Порядок разработки системы
│   ├── layer-0/             # 🟥 Doctrine / Конституция системы
│   │   ├── README.md        # Описание Layer 0
│   │   ├── ARCHITECTURE_LOCK.md
│   │   ├── CONCEPT.md
│   │   ├── DOMAIN_MODEL.md
│   │   ├── LLM_USAGE_POLICY.md
│   │   ├── LEARNING_MEMORY_POLICY.md
│   │   └── USAGE_DOCTRINE.md
│   ├── layer-1/             # 🟧 System Design / Logical Architecture
│   │   ├── README.md        # Описание Layer 1
│   │   ├── CANONICAL_SCHEMA.md
│   │   ├── DECISION_ENGINE.md
│   │   └── DATA_CONTRACTS.md
│   ├── layer-2/             # 🟨 Product & Integration Specs
│   │   └── README.md        # Описание Layer 2 (в разработке)
│   └── layer-3/             # 🟩 Implementation & Infra
│       └── README.md        # Описание Layer 3 (в разработке)
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
- ✅ **Concept Document** - [Concept Document](./docs/layer-0/CONCEPT.md) (v1.0)
- ✅ **Architecture Lock** - [Architecture Lock / Doctrine](./docs/layer-0/ARCHITECTURE_LOCK.md) (v1.0)
- ✅ **Domain Model** - [Domain Model / Glossary](./docs/layer-0/DOMAIN_MODEL.md) (v1.0)
- ✅ **LLM Usage Policy** - [LLM Usage Policy](./docs/layer-0/LLM_USAGE_POLICY.md) (v1.0)
- ✅ **Learning & Memory Policy** - [Learning & Memory Policy](./docs/layer-0/LEARNING_MEMORY_POLICY.md) (v1.2)
- ✅ **Usage & Interaction Doctrine** - [Usage & Interaction Doctrine](./docs/layer-0/USAGE_DOCTRINE.md) (v1.1)

**🟧 Layer 1 — System Design:**
- ✅ **Canonical Schema** - [Canonical Schema Specification](./docs/layer-1/CANONICAL_SCHEMA.md) (v1.2)
- ✅ **Decision Engine** - [Decision Engine Specification](./docs/layer-1/DECISION_ENGINE.md) (v1.1)
- ✅ **Data Contracts** - [Data Contracts Specification](./docs/layer-1/DATA_CONTRACTS.md) (v1.0)

**🟨 Layer 2 — Product & Integration:** (в разработке)  
**🟩 Layer 3 — Implementation & Infra:** (в разработке)
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
1. Начните с [Concept Document](./docs/layer-0/CONCEPT.md) — общее понимание системы
2. Изучите [Architecture Lock](./docs/layer-0/ARCHITECTURE_LOCK.md) — это основа всех решений
3. Изучите [Domain Model](./docs/layer-0/DOMAIN_MODEL.md) — единый язык системы
4. Ознакомьтесь с [Canonical Schema](./docs/layer-1/CANONICAL_SCHEMA.md) — структура данных
5. Изучите [Data Contracts](./docs/layer-1/DATA_CONTRACTS.md) — контракты входных данных
6. Прочитайте [LLM Usage Policy](./docs/layer-0/LLM_USAGE_POLICY.md) — правила использования LLM
7. Изучите [Learning & Memory Policy](./docs/layer-0/LEARNING_MEMORY_POLICY.md) — обучение и память системы
8. Прочитайте [Decision Engine Specification](./docs/layer-1/DECISION_ENGINE.md) — ядро системы
9. Изучите [Usage & Interaction Doctrine](./docs/layer-0/USAGE_DOCTRINE.md) — как медиабайер взаимодействует с системой
10. Следуйте [Development Order](./docs/DEVELOPMENT_ORDER.md) для разработки
11. Спросите у меня (AI помощника) - я помогу!

---

**Удачи в разработке! 🎉**
