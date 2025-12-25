# GenomAI Spheres

Система разбита на независимые сферы для модульного патчинга.

## Сферы

| # | Сфера | Label | Описание |
|---|-------|-------|----------|
| 1 | **Ingestion** | `sphere:ingestion` | Приём видео, транскрипция |
| 2 | **Decomposition** | `sphere:decomposition` | LLM-разбор на переменные (Canonical Schema) |
| 3 | **Idea Registry** | `sphere:idea-registry` | Управление идеями, дедупликация, кластеры |
| 4 | **Decision Engine** | `sphere:decision-engine` | 4 проверки → APPROVE/REJECT/DEFER |
| 5 | **Hypothesis Factory** | `sphere:hypothesis-factory` | Генерация исполнимых транскриптов |
| 6 | **Delivery** | `sphere:delivery` | Отправка в Telegram |
| 7 | **Metrics Collection** | `sphere:metrics` | Keitaro polling, snapshots |
| 8 | **Outcome Processing** | `sphere:outcomes` | Агрегация, обогащение контекстом |
| 9 | **Learning Loop** | `sphere:learning` | Обновление confidence/fatigue |
| 10 | **Buyer System** | `sphere:buyer` | Баеры, их креативы, отчёты |

## Описание сфер

### 1. Ingestion
**Вход данных в систему**
- Принимает видео креативов через Telegram бота
- Извлекает аудио, отправляет на транскрипцию (Whisper/AssemblyAI)
- Сохраняет креатив в `creatives` с транскриптом
- *Без этого:* система не получает сырьё для анализа

### 2. Decomposition
**LLM-разбор транскрипта**
- Парсит транскрипт в структурированные переменные (Canonical Schema)
- Извлекает: hook, pain points, CTA, offer structure, tone
- Работает ТОЛЬКО с текстом, не с визуалами
- *Без этого:* нет переменных для сравнения и обучения

### 3. Idea Registry
**Реестр уникальных идей**
- Дедупликация через `canonical_hash`
- Кластеризация похожих идей (`cluster_id`)
- Хранит "чистые" идеи отдельно от конкретных креативов
- *Без этого:* одна идея считалась бы много раз

### 4. Decision Engine
**Ядро системы — 4 проверки**
- Schema Validity → структура корректна?
- Death Memory → идея уже "мертва"?
- Fatigue Constraint → аудитория не устала?
- Risk Budget → есть бюджет на риск?
- Выход: APPROVE / REJECT / DEFER
- *Без этого:* нет детерминированных решений

### 5. Hypothesis Factory
**Генерация исполнимых гипотез**
- Берёт APPROVED идею
- Генерирует конкретный исполнимый транскрипт для баера
- Добавляет контекст, вариации
- *Без этого:* идея не превращается в action item

### 6. Delivery
**Доставка в Telegram**
- Форматирует гипотезу для баера
- Отправляет в нужный чат
- Логирует доставку в `deliveries`
- *Без этого:* баер не получает задания

### 7. Metrics Collection
**Сбор метрик из Keitaro**
- Pull-based polling (не push)
- Снимает текущие метрики → `raw_metrics_current`
- Создаёт daily snapshots → `daily_metrics_snapshot`
- *Без этого:* нет данных о результатах

### 8. Outcome Processing
**Обработка результатов**
- Агрегирует сырые метрики в outcomes
- Обогащает контекстом (какая идея, какой креатив)
- Определяет success/failure по порогам
- *Без этого:* метрики не связаны с идеями

### 9. Learning Loop
**Обучение системы**
- Обновляет `confidence` идей на основе outcomes
- Обновляет `fatigue` по сегментам
- Time decay для устаревших данных
- Влияет на будущие решения Decision Engine
- *Без этого:* система не учится на результатах

### 10. Buyer System
**Управление баерами**
- Регистрация креативов баеров
- Трекинг тестов, выводы (win/lose)
- Daily digest, статистика
- Связывает outcomes с конкретными баерами
- *Без этого:* нет персонализации по исполнителям

## Компоненты по сферам

### 1. Ingestion
- **n8n:** `creative_ingestion_webhook` (dvZvUUmhtPzYOK7X)
- **n8n:** `GenomAI - Creative Transcription` (WMnFHqsFh8i7ddjV)
- **Таблицы:** `creatives`
- **Внешние:** Telegram Bot API, Whisper/AssemblyAI

### 2. Decomposition
- **n8n:** `creative_decomposition_llm` (mv6diVtqnuwr7qev)
- **Таблицы:** читает `creatives`
- **Внешние:** OpenAI/Anthropic API
- **Важно:** Только транскрипты, не визуалы

### 3. Idea Registry
- **n8n:** `idea_registry_create` (cGSyJPROrkqLVHZP)
- **Таблицы:** `ideas`
- **Логика:** `canonical_hash` дедупликация, `cluster_id`

### 4. Decision Engine
- **FastAPI:** `decision-engine-service/src/`
- **n8n:** `decision_engine_mvp` (YT2d7z5h9bPy1R4v)
- **Таблицы:** `decisions`, `decision_traces`
- **Checks:**
  - `schema_validity.py` → REJECT
  - `death_memory.py` → REJECT
  - `fatigue_constraint.py` → REJECT
  - `risk_budget.py` → DEFER

### 5. Hypothesis Factory
- **n8n:** `hypothesis_factory_generate` (oxG1DqxtkTGCqLZi)
- **Таблицы:** `hypotheses`
- **Внешние:** LLM API

### 6. Delivery
- **n8n:** `Telegram Hypothesis Delivery` (5q3mshC9HRPpL6C0)
- **Таблицы:** `deliveries`
- **Внешние:** Telegram Bot API

### 7. Metrics Collection
- **n8n:** `Keitaro Poller` (0TrVJOtHiNEEAsTN)
- **n8n:** `Snapshot Creator` (Gii8l2XwnX43Wqr4)
- **Таблицы:** `raw_metrics_current`, `daily_metrics_snapshot`
- **Внешние:** Keitaro API

### 8. Outcome Processing
- **n8n:** `Outcome Aggregator` (243QnGrUSDtXLjqU)
- **n8n:** `Outcome Processor` (bbbQC4Aua5E3SYSK)
- **Таблицы:** `outcome_aggregates`

### 9. Learning Loop
- **n8n:** `Learning Loop v2` (fzXkoG805jQZUR3S)
- **Таблицы:** `idea_confidence_versions`, `fatigue_state_versions`
- **Важно:** Только `system` outcomes → causal updates

### 10. Buyer System
- **n8n:** `Buyer Creative Registration` (d5i9dB2GNqsbfmSD)
- **n8n:** `Buyer Test Conclusion Checker` (4uluD04qYHhsetBy)
- **n8n:** `Buyer Daily Digest` (WkS1fPSxZaLmWcYy)
- **n8n:** `Buyer Stats Command` (rHuT8dYyIXoiHMAV)
- **Таблицы:** `buyers`, `buyer_states`, `component_learnings`

## Граф зависимостей

```
[1] Ingestion
      ↓
[2] Decomposition
      ↓
[3] Idea Registry
      ↓
[4] Decision Engine ←──────────────────┐
      ↓                                │
[5] Hypothesis Factory                 │
      ↓                                │
[6] Delivery                           │
      ↓                                │
   (Execution in Keitaro)              │
      ↓                                │
[7] Metrics Collection                 │
      ↓                                │
[8] Outcome Processing                 │
      ↓                                │
[9] Learning Loop ─────────────────────┘
      │
      └──→ Updates confidence/fatigue → affects [4]

[10] Buyer System — параллельный поток, использует [7], [9]
```

## Branching Convention

```
patch/<sphere>-<short-description>
```

Примеры:
- `patch/ingestion-add-validation`
- `patch/decision-engine-fix-trace`
- `patch/learning-update-formula`
