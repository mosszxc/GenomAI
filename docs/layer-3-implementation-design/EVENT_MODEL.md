# Event Model Specification
## GenomAI — Canonical Event Model (Layer 3)

**Версия:** v1.1  
**Статус:** CANONICAL / LAYER 3  
**Приоритет:** Критический  
**Основан на:** SERVICE_BOUNDARIES, STORAGE_MODEL, ENTITY_LIFECYCLE, LEARNING_MEMORY_POLICY, MVP_SCOPE

---

## 1. Purpose

Документ фиксирует жизненный цикл фактов во времени в системе GenomAI:
- какие события существуют,
- когда они происходят,
- какие события не означают outcome,
- какие события единственные допустимые входы в learning.

Документ описывает **факты, а не команды**.  
Транспорт, очереди и cron-механики вне scope.

---

## 2. Core Temporal Principle

**Метрики — это поток.**  
**Outcome — это агрегированное состояние за окно.**  
**Learning возможен только после закрытия окна.**

Ни одно событие, отражающее сырое или промежуточное состояние,  
не может напрямую влиять на Decision или Learning.

---

## 3. Event Taxonomy

Все события делятся на 5 классов:

1. **Ingestion Events** — приход внешних фактов
2. **Metric Observation Events** — фиксация метрик
3. **Temporal Aggregation Events** — закрытие периодов
4. **Decision & Execution Events** — решения и генерация
5. **Learning Events** — обновление памяти

---

## 4. Ingestion Events

### 4.1 CreativeReferenceReceived

**Описание:**  
Получена ссылка на видео и tracker_id.

**Источник:** Ingestion Service  
**Обязательное:** ✅  
**Идемпотентное:** ✅ (tracker_id + video_url)

**Важно:**  
Событие не означает, что данные валидны или обработаны.

---

### 4.2 RawMetricsObserved

**Описание:**  
Получено обновление сырых метрик из трекера.

**Источник:** Outcome Ingestion Service  
**Обязательное:** ❌  
**Идемпотентное:** ❌

**Семантика:**
- шумное
- неполное
- может перезаписываться
- **НИКОГДА не используется напрямую**

---

## 5. Metric Observation Events (Daily Scan)

### 5.1 DailyMetricsSnapshotCreated

**Описание:**  
Зафиксирован снимок состояния креатива за прошедший день.

**Источник:** Metrics Scanner  
**Обязательное:** ❌  
**Идемпотентное:** ✅ (creative_id + date)

**Гарантии:**
- 1 snapshot = 1 день
- snapshot immutable
- snapshot не интерпретируется

---

## 6. Temporal Aggregation Events

### 6.1 OutcomeWindowClosed

**Описание:**  
Факт завершения временного окна (например, D1–D3, D1–D7).

**Источник:** Aggregation Engine  
**Обязательное:** ❌  
**Идемпотентное:** ✅ (creative_id + window_id)

**Важно:**  
Закрытие окна не означает, что outcome хороший или плохой.

---

### 6.2 OutcomeAggregated

**Описание:**  
Создан агрегированный Outcome за закрытое окно.

**Источник:** Aggregation Engine  
**Обязательное:** ❌  
**Идемпотентное:** ✅

**Содержит:**
- агрегированные метрики
- динамические признаки (trend, volatility, saturation)
- environment_context
- origin_type (system | user)
- decision_id (nullable, обязателен для `origin_type = system`)

**Критическое правило:**
- `origin_type = system` → требует Decision (decision_id обязателен)
- `origin_type = user` → допускается без Decision (decision_id может быть NULL)

👉 **Это единственный допустимый Outcome в системе.**

---

## 7. Decision & Execution Events

### 7.1 DecisionMade

**Источник:** Decision Engine  
**Идемпотентное:** ✅ (idea_id + decision_epoch)

---

### 7.2 HypothesisGenerated

**Источник:** Hypothesis Factory  
**Идемпотентное:** ✅

---

### 7.3 HypothesisDelivered

**Источник:** Delivery Boundary  
**Идемпотентное:** ✅

---

## 8. Learning Events

### 8.1 OutcomeAppliedToLearning

**Описание:**  
Outcome учтён в Learning Memory.

**Источник:** Learning Loop  
**Обязательное:** ❌  
**Идемпотентное:** ❌

⚠️ **Критично:**
- допускается строго один раз
- только если:
  - `origin_type = system`
  - Outcome получен из OutcomeAggregated

---

## 9. Canonical Event Flow (важно)

```
CreativeReferenceReceived
        ↓
RawMetricsObserved (many, ignored)
        ↓
DailyMetricsSnapshotCreated (daily)
        ↓
DailyMetricsSnapshotCreated
        ↓
OutcomeWindowClosed
        ↓
OutcomeAggregated
        ↓
OutcomeAppliedToLearning
```

**Любой обход этой цепочки — архитектурное нарушение.**

---

## 10. Forbidden Event Patterns

**Запрещено:**
- Learning на RawMetricsObserved
- Learning на DailyMetricsSnapshotCreated
- Decision на основе snapshot или raw
- Повтор OutcomeAppliedToLearning
- Пересоздание OutcomeAggregated

---

## 11. Failure Semantics (кратко)

- нет snapshot за день → окно может не закрыться
- неполные метрики → snapshot всё равно создаётся
- пропущенное окно → learning не происходит

**Система предпочитает ничего не сделать, чем сделать неверно.**

---

## 12. Evolution Rule

Добавление события допустимо, если:
- оно отражает новый факт во времени
- не превращает событие в команду
- не нарушает принцип: **learning только после агрегированного окна**

---

## 13. Final Rule

**Если событие отражает "прямо сейчас", оно не может влиять на будущее решений.**

---

## 14. Layer Boundary Notice

Этот документ:
- завершает Event-часть Layer 3,
- не описывает транспорт событий (очереди, pub/sub),
- не описывает cron-механики или триггеры.
