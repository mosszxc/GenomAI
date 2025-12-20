# GenomAI Documentation

> Полная документация системы GenomAI — Autonomous Creative Decision System

---

## Структура документации

Документация организована в 5 слоёв:

### 🟥 Layer 0 — Doctrine / Конституция системы
**Фундаментальные принципы, правила и политики системы.**

📁 [layer-0-doctrine/](./layer-0-doctrine/)

### 🟧 Layer 1 — System Design / Logical Architecture
**Логическая архитектура системы. Спецификации компонентов, схемы данных, контракты.**

📁 [layer-1-logic/](./layer-1-logic/)

### 🟨 Layer 2 — Product & Integration Specs
**Спецификации продукта и интеграций. API, интерфейсы, интеграционные контракты.**

📁 [layer-2-product/](./layer-2-product/)

### 🟩 Layer 3 — Implementation Design
**Спецификации реализации и инфраструктуры. Логические сервисы, технологии, деплой.**

📁 [layer-3-implementation-design/](./layer-3-implementation-design/)

### 🟦 Layer 4 — Implementation Planning
**Планы реализации и технические детали. Конкретные технологии, схемы БД, API контракты.**

📁 [layer-4-implementation-planning/](./layer-4-implementation-planning/)

---

## Порядок изучения

1. **Начните с [Layer 0](./layer-0-doctrine/)** — это основа всех решений
2. **Изучите [Layer 1](./layer-1-logic/)** — логическая архитектура системы
3. **Ознакомьтесь с [Layer 2](./layer-2-product/)** — спецификации продукта
4. **Изучите [Layer 3](./layer-3-implementation-design/)** — спецификации реализации
5. **Используйте [Layer 4](./layer-4-implementation-planning/)** — планы реализации

---

## Дополнительные документы

📋 **[Development Order](./DEVELOPMENT_ORDER.md)** — Строгий порядок разработки системы

---

## Правила изменения документации

- **Layer 0** — изменения требуют архитектурного ревью
- **Layer 1** — изменения должны быть совместимы с Layer 0
- **Layer 2** — изменения должны быть совместимы с Layer 0 и Layer 1
- **Layer 3** — технические детали могут меняться чаще
- **Layer 4** — планы реализации могут изменяться часто

---

**Удачи в разработке! 🎉**
