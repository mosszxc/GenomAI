# BMad Method - Quick Start для GenomAI

## ✅ Установка завершена!

BMad Method v6.0.0-alpha.19 установлен и готов к использованию.

## 🚀 Следующие шаги

### Шаг 1: Инициализация проекта (опционально)

**Для первого знакомства с BMad Method:**

1. В Cursor откройте новый чат
2. Упомяните: `@bmad/bmm/agents/analyst`
3. Напишите: `*workflow-init`
4. BMad проанализирует проект GenomAI и предложит подходящий track

**Это поможет:**
- Понять, как BMad видит ваш проект
- Получить рекомендации по workflow track
- Сгенерировать project context

---

### Шаг 2: Работа над STEP 07 (Outcome Ingestion)

**Сейчас вы работаете над STEP 07 - Outcome Ingestion.**

#### Вариант A: Создать PRD для STEP 07

1. В Cursor откройте новый чат
2. Упомяните: `@bmad/bmm/agents/pm`
3. Напишите: `*create-prd`
4. Укажите контекст: "STEP 07 - Outcome Ingestion для GenomAI"
5. Ссылайтесь на playbook: `docs/layer-4-implementation-planning/STEP_IMPLEMENTATION_PLAYBOOKS/07_outcome_ingestion_playbook.md`

**Результат:** Структурированный PRD для Outcome Ingestion

#### Вариант B: Создать Tech Spec для STEP 07

1. В Cursor откройте новый чат
2. Упомяните: `@bmad/bmm/agents/pm`
3. Напишите: `*create-tech-spec`
4. Укажите контекст: "STEP 07 - Outcome Ingestion, n8n workflow для Keitaro API"

**Результат:** Детальный технический спецификация для реализации

#### Вариант C: Получить помощь в реализации n8n workflow

1. В Cursor откройте новый чат
2. Упомяните: `@bmad/bmm/agents/dev`
3. Опишите задачу: "Помоги реализовать n8n workflow для STEP 07 - Outcome Ingestion"
4. Приложите playbook: `07_outcome_ingestion_playbook.md`

**Результат:** Помощь в создании n8n workflow с правильной структурой

---

## 📋 Доступные агенты для GenomAI

### Для планирования:
- **@bmad/bmm/agents/pm** - Product Manager
  - `*create-prd` - Product Requirements Document
  - `*create-tech-spec` - Technical Specification
  - `*create-product-brief` - Product Brief

### Для архитектуры:
- **@bmad/bmm/agents/architect** - Architect
  - `*create-architecture` - Architecture Design (для 10+ stories)
  - `*check-implementation-readiness` - Проверка готовности к реализации

### Для разработки:
- **@bmad/bmm/agents/dev** - Developer
  - `*dev-story` - Реализация story
  - `*quick-dev` - Быстрая разработка
  - `*code-review` - Code Review

### Для тестирования:
- **@bmad/bmm/agents/tea** - Test Architect
  - `*testarch-test-design` - Дизайн тестов
  - `*testarch-framework` - Framework для тестов

### Для анализа:
- **@bmad/bmm/agents/analyst** - Analyst
  - `*workflow-init` - Инициализация проекта
  - `*research` - Исследование

---

## 🎯 Рекомендуемый workflow для STEP 07

1. **PM Agent → PRD** (если нужен структурированный документ)
2. **PM Agent → Tech Spec** (для детальной технической спецификации)
3. **Developer Agent → dev-story** (для реализации n8n workflow)
4. **Test Architect → test-design** (для тестовых сценариев)

---

## 💡 Важные правила

1. **Всегда используйте свежие чаты** для каждого workflow (избегайте галлюцинаций)
2. **Упоминайте агентов через @** - `@bmad/bmm/agents/pm`
3. **Используйте команды с * ** - `*create-prd`, `*workflow-init`
4. **Прикладывайте контекст** - ссылайтесь на playbooks и документацию

---

## 📚 Документация

- Полный индекс: `@bmad/index`
- Все агенты: `.cursor/rules/bmad/bmm/agents/`
- Все workflows: `.cursor/rules/bmad/bmm/workflows/`

---

## 🎬 Начните сейчас!

**Для STEP 07 рекомендую начать с:**

```
@bmad/bmm/agents/pm

*create-tech-spec

Контекст: STEP 07 - Outcome Ingestion для GenomAI
Playbook: docs/layer-4-implementation-planning/STEP_IMPLEMENTATION_PLAYBOOKS/07_outcome_ingestion_playbook.md

Нужно создать n8n workflow для:
- Pull metrics из Keitaro API
- Сохранение в raw_metrics_current
- Создание daily_metrics_snapshot
- Emit событий RawMetricsObserved и DailyMetricsSnapshotCreated
```

Это создаст детальную техническую спецификацию для реализации!

