# Environment Context Specification
## GenomAI — Environment Context & Noise Handling (Layer 1)

**Версия:** v1.0  
**Статус:** CANONICAL / LAYER 1  
**Приоритет:** Высокий  
**Основан на:** ARCHITECTURE_LOCK, ENTITY_LIFECYCLE, LEARNING_MEMORY_POLICY

---

## 1. Purpose

Данный документ определяет как система GenomAI учитывает факторы среды исполнения (environment context) при интерпретации Outcome, не используя их для принятия решений.

**Цель:**
- различать эффект идеи и эффект среды исполнения
- корректно интерпретировать Outcome в контексте environment
- предотвратить использование environment как escape hatch для оправдания плохих решений

Документ:
- не описывает инфраструктуру или технологии
- фиксирует семантику environment context, а не реализацию

---

## 2. Core Environment Principle

**Environment Separation:**
- Система различает эффект идеи и эффект среды исполнения
- Факторы среды (account state, platform state, auction pressure) не являются основанием для принятия решений Decision Engine
- Environment используется только для корректной интерпретации Outcome в Learning Loop
- **Environment не является escape hatch для оправдания плохих решений**

---

## 3. Environment Context Fields

### 3.1 Account State

**Возможные значения:**
- `unknown` — состояние неизвестно (по умолчанию)
- `stable` — аккаунт стабилен, без известных проблем
- `degraded` — аккаунт в деградированном состоянии (learning phase, bans, resets)

---

### 3.2 Platform State

**Возможные значения:**
- `normal` — платформа работает нормально
- `volatile` — платформа нестабильна (известные проблемы, обновления)

---

### 3.3 Auction Pressure

**Возможные значения:**
- `low` — низкое давление аукциона
- `normal` — нормальное давление
- `high` — высокое давление аукциона

---

## 4. Environment Context Usage

### 4.1 In Outcome Entity

**Outcome может содержать опциональные метаданные о среде исполнения:**

- `environment_context` (опционально):
  - `account_state`: unknown | stable | degraded
  - `platform_state`: normal | volatile
  - `auction_pressure`: low | normal | high

**Важно:**
- Это **metadata**, не обязательные поля
- Outcome **валиден без environment_context**
- Environment context используется только Learning Loop для корректной интерпретации Outcome
- Decision Engine **не читает environment_context** напрямую

---

### 4.2 In Learning Loop

**Environment Context Weighting:**
- Outcome updates memory relative to environment context
- Плохой outcome в degraded environment:
  - ❌ не убивает идею
  - ❌ не снижает confidence резко
- Хороший outcome в degraded environment:
  - ✅ повышает confidence сильнее обычного
- **Это не нормализация, это мягкое весовое смещение**

---

## 5. Decision Engine Blindness

**Критическое правило:**  
Decision Engine **"слеп" к environment** — не читает environment_context напрямую.

**Learning Loop интерпретирует Outcome относительно environment** для корректного весового смещения.

**Environment не является основанием для решений, только для корректной интерпретации результатов.**

---

## 6. Forbidden Patterns

**Запрещено:**
- Decision Engine использовать environment_context для принятия решений
- Объяснять пользователю плохие решения через environment (например: "фб ныл", "аккаунт плохой")
- Использовать environment как escape hatch для оправдания плохих решений
- Требовать environment_context для валидации Outcome

---

## 7. Input Normalization

**Media Buyer может передать (опционально):**
- `account_state`: unknown | stable | degraded
- `platform_state`: normal | volatile
- `auction_pressure`: low | normal | high
- known issues (learning phase, bans, resets)

**Важно:**
- Это **advisory** данные, не обязательные
- Отсутствие данных = `unknown` (по умолчанию)
- Система **не требует** environment signals
- Environment используется только Learning Loop для корректной интерпретации Outcome
- **Environment не влияет на Decision Engine**

---

## 8. Final Rule

**Environment — это корректирующий фактор внутри системы, не раскрывается в output.**

**Внутреннее поведение ≠ пользовательское объяснение.**

---

## 9. Layer Boundary Notice

Этот документ:
- завершает Environment Context-часть Layer 1,
- не описывает инфраструктуру или технологии,
- не описывает UI или пользовательские интерфейсы.
