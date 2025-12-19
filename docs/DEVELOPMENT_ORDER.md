# GenomAI — Development Order
## Порядок разработки системы (engineering roadmap)

Документ описывает **строгий порядок разработки** системы GenomAI.
Нарушение порядка приводит к переделкам, деградации логики и потере контроля.

---

## PHASE 0 — Architectural Lock (обязательный старт)

### Цель
Зафиксировать границы ответственности до любого кода.

### Делается
- Зафиксировать:
  - Decision Engine = rules / if-then
  - ML = advisory (signals, scores), не решения
  - LLM = классификация и генерация, не выбор
  - n8n = orchestration, не логика
- Зафиксировать:
  - exploit / explore / shock
  - горизонты T1 / T2 / T3
- Запретить:
  - LLM-decision
  - end-to-end RL
  - автоматизацию без decision trace

### Артефакты
- `ARCHITECTURE_LOCK.md`
- `DECISION_BOUNDARIES.md`

---

## PHASE 1 — Domain Modeling (язык системы)

### Цель
Определить, **о чём вообще думает система**.

### Делается
- Выделяются доменные сущности:
  - Idea
  - Hypothesis
  - Outcome
  - Cluster
  - Decision
  - State
- Без полей, только сущности и связи

### Артефакты
- `domain_entities.md`

---

## PHASE 2 — Core Variable Definition (самый критичный этап)

### Цель
Создать **алфавит мышления системы**.

### Делается
- Определяется core-набор переменных для Idea:
  - angle_type
  - core_belief
  - promise_type
  - emotion_primary
  - emotion_intensity
  - message_structure
  - idea_cluster_id
  - source_type
- Переменные:
  - минимальные
  - дискретные (enum)
  - без дублирования смысла
- Всё лишнее выкидывается

### Артефакты
- `idea_variables.md`

---

## PHASE 3 — Canonical Schema (single source of truth)

### Цель
Зафиксировать переменные так, чтобы их нельзя было «обойти».

### Делается
- Переменные оформляются как schema:
  - JSON Schema / Pydantic / TS types
- Фиксируются:
  - типы
  - enum-значения
  - обязательность
- Включается версионирование

### Правило
Если поля нет в schema — его не существует.

### Артефакты
- `/schemas/idea.schema.json`
- `/schemas/outcome.schema.json`

---

## PHASE 4 — Schema Validation (проверка на реальность)

### Цель
Проверить, что язык реально описывает рынок.

### Делается
- Берутся 3–5 реальных креативов
- Каждый креатив кодируется ТОЛЬКО по schema
- Запрещено добавлять новые поля

### Результат
- Если не хватает полей → schema слабая
- Если хочется добавить всё подряд → schema перегружена

### Артефакты
- `schema_validation.md`

---

## PHASE 5 — Storage & Memory Layer

### Цель
Система ничего не забывает.

### Делается
- Проектируется БД:
  - ideas
  - hypotheses
  - outcomes
  - clusters
  - fatigue_state
  - death_memory
- Фиксируется:
  - что считается смертью идеи
  - что считается выгоранием
  - что считается похожестью

### Артефакты
- `db_schema.sql`
- `memory_rules.md`

---

## PHASE 6 — Input & Ingestion Layer

### Цель
Аккуратно завести внешний мир.

### Делается
- Подключаются источники:
  - performance data
  - свои креативы
  - spy-креативы
- Делается нормализация:
  - context
  - source_type
- Добавляются флаги:
  - trusted / noisy
  - anomaly

### Инструменты
- n8n / Airflow / Temporal

### Артефакты
- `ingestion_flows/`
- `data_quality_rules.md`

---

## PHASE 7 — Decomposition Layer (первое место для LLM)

### Цель
Превратить сырьё в структуру.

### Делается
- LLM используется ТОЛЬКО для:
  - классификации по schema
- LLM:
  - не принимает решений
  - не создаёт новые поля

### Артефакты
- `llm_prompts/`
- `decomposition_service.py`

---

## PHASE 8 — Similarity / Novelty / Clustering

### Цель
Сделать идеи сравнимыми.

### Делается
- Embeddings для идей
- similarity_score
- novelty_score
- присвоение idea_cluster_id

### Правило
ML возвращает числа, не решения.

### Артефакты
- `similarity_service.py`

---

## PHASE 9 — Fatigue & Death Systems

### Цель
Не повторять мёртвое и не выжигать рынок.

### Делается
- Fatigue Engine (skin → message → angle)
- Death Memory (soft / hard / dead)
- Resurrection только через override

### Артефакты
- `fatigue_engine.py`
- `death_memory.py`

---

## PHASE 10 — Decision Engine (ядро)

### Цель
Решать, какие идеи допустимы.

### Делается
- Детерминированный pipeline:
  - death check
  - fatigue check
  - pseudo-novelty check
  - context validity
  - risk budget
  - confidence / shock
- Фиксированный порядок проверок
- Decision trace обязателен

### Артефакты
- `decision_engine.py`
- `rules.yaml`
- `decision_trace.log`

---

## PHASE 11 — Hypothesis Factory

### Цель
Превратить решение в варианты исполнения.

### Делается
- Генерация вариантов
- Ограничение радиуса мутаций
- Привязка к одной Idea

### Артефакты
- `hypothesis_factory.py`

---

## PHASE 12 — Execution Layer

### Цель
Отдать решение рынку без эмоций.

### Делается
- Автозапуск
- Budget / time caps
- Минимум ручных вмешательств

### Артефакты
- `execution_service.py`

---

## PHASE 13 — Outcome Logging

### Цель
Зафиксировать факт, не интерпретацию.

### Делается
- Логирование:
  - ожидание
  - факт
  - контекст
- Без выводов

### Артефакты
- `outcomes_table`
- `logging_service.py`

---

## PHASE 14 — Horizon Evaluation

### Цель
Не делать ранних выводов.

### Делается
- Раздельная оценка T1 / T2 / T3
- Запрет выводов вне горизонта

### Артефакты
- `horizon_evaluator.py`

---

## PHASE 15 — Learning Loop

### Цель
Изменить будущее поведение системы.

### Делается
- Обновление:
  - weights
  - fatigue
  - death
- Учет time-decay знаний

### Артефакты
- `learning_loop.py`

---

## PHASE 16 — Epistemic Shock & Regime Detection

### Цель
Не зациклиться навсегда.

### Делается
- Forced exploration
- Regime change detection
- Изолированный budget

### Артефакты
- `shock_engine.py`

---

## PHASE 17 — Human Override Layer

### Цель
Человек ломает рамку, не систему.

### Делается
- Ограниченный набор override
- Полное логирование
- Нет ручного выбора идей

### Артефакты
- `override_service.py`

---

## Ключевое правило

**Любой этап нельзя начинать, если предыдущий не зафиксирован документально.**
