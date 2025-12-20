# Layer 1 — System Design / Logical Architecture

**Статус:** CANONICAL  
**Приоритет:** Высокий

---

## Назначение

Layer 1 содержит **логическую архитектуру системы** — спецификации компонентов, схемы данных, контракты.

Эти документы:
- описывают **логическую структуру** системы
- определяют **компоненты и их ответственность**
- фиксируют **схемы данных** и **контракты**
- устанавливают **правила взаимодействия**

**Layer 1 должен соответствовать Layer 0.**

---

## Документы Layer 1

🏗️ **[System Architecture](./SYSTEM_ARCHITECTURE.md)** — Логическая архитектура системы (v1.0)

📚 **[Domain Model](./DOMAIN_MODEL.md)** — Единый словарь предметной области (v1.0)

🔁 **[Entity Lifecycle](./ENTITY_LIFECYCLE.md)** — Жизненный цикл и владение сущностями (v1.0)

📐 **[Canonical Schema](./CANONICAL_SCHEMA.md)** — Каноническая схема данных (v1.2)

🔄 **[Data Flow](./DATA_FLOW.md)** — Канонический поток данных и жизненный цикл объектов (v1.0)

⚙️ **[Decision Engine](./DECISION_ENGINE.md)** — Детерминированное ядро системы (v1.1)

🧠 **[Learning & Memory Policy](./LEARNING_MEMORY_POLICY.md)** — Политика обучения и памяти (v1.2)

🔒 **[Data Contracts](./DATA_CONTRACTS.md)** — Контракты входных данных (v1.0)

🤖 **[LLM Usage Policy](./LLM_USAGE_POLICY.md)** — Политика использования LLM (v1.0)

🌍 **[Environment Context](./ENVIRONMENT_CONTEXT.md)** — Environment Context & Noise Handling (v1.0)

---

## Правила изменения

- Изменения должны быть **совместимы с Layer 0**
- Breaking changes требуют **архитектурного ревью**
- Требуется **документирование** изменений

---

## Связь с другими слоями

- **Основан на:** Layer 0 (Doctrine)
- **Реализуется:** Layer 2 (Product & Integration), Layer 3 (Implementation Design), Layer 4 (Implementation Planning)

**Layer 1 — это логическая архитектура системы.**
