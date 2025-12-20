# Error Handling Specification
## GenomAI — Error Handling & Failure Semantics (Layer 3)

**Версия:** v1.0  
**Статус:** CANONICAL / LAYER 3  
**Приоритет:** Критический  
**Основан на:** SERVICE_BOUNDARIES, EVENT_MODEL v1.1, STORAGE_MODEL, LEARNING_MEMORY_POLICY

---

## 1. Purpose

Документ определяет как система GenomAI ведёт себя при сбоях, неполных данных и неопределённых состояниях.

**Цель:**
- предотвратить тихую деградацию обучения,
- исключить частичное или ложное learning-обновление,
- зафиксировать safe-defaults для всех критических точек.

Документ:
- не описывает инфраструктурные ошибки,
- не содержит retry-механик конкретных технологий,
- описывает семантику поведения, а не реализацию.

---

## 2. Core Failure Principle

**Лучше не обучиться, чем обучиться неправильно.**

Из этого принципа следуют все правила ниже.

---

## 3. Error Classes

Все ошибки в системе классифицируются по семантическому типу, а не по источнику.

### 3.1 Data Absence

Данные отсутствуют или неполны.

**Примеры:**
- нет метрик за день
- нет snapshot
- окно не может быть закрыто

---

### 3.2 Data Delay

Данные пришли с опозданием.

**Примеры:**
- трекер обновил данные через 48 часов
- daily scan пропущен

---

### 3.3 Data Duplication

События или данные пришли повторно.

**Примеры:**
- повтор DailyMetricsSnapshotCreated
- повтор OutcomeAggregated

---

### 3.4 Processing Failure

Внутренняя ошибка сервиса.

**Примеры:**
- aggregation failed
- learning update aborted

---

### 3.5 Semantic Violation

Нарушение архитектурных правил.

**Примеры:**
- попытка learning на raw metrics
- outcome без закрытого окна
- system decision на user-origin outcome

---

## 4. Handling Rules by Layer

### 4.1 Raw Metrics Layer (L1)

**Сценарии:**
- метрики отсутствуют
- метрики противоречивы
- метрики обновляются задним числом

**Поведение:**
- данные принимаются
- данные могут быть перезаписаны
- никаких downstream эффектов

**Retry:**  
✅ **Да**

**Safe Default:**  
Отсутствие метрик ≠ ошибка системы.

---

### 4.2 Daily Snapshot Layer (L2)

**Сценарии:**
- snapshot не создан за день
- snapshot создан с нулевыми значениями
- snapshot продублирован

**Поведение:**
- отсутствие snapshot допустимо
- дубль snapshot игнорируется
- snapshot никогда не пересоздаётся

**Retry:**  
✅ **Да** (creation)  
❌ **Нет** (mutation)

**Safe Default:**  
Нет snapshot → нет сигнала → ждём.

---

### 4.3 Outcome Aggregation Layer (L3)

**Сценарии:**
- окно не может быть закрыто
- недостаточно snapshot'ов
- данные нестабильны

**Поведение:**
- окно не закрывается
- Outcome не создаётся
- learning не запускается

**Retry:**  
❌ **Нет** (по инициативе системы)  
Окно может быть закрыто позже автоматически.

**Safe Default:**  
Нет Outcome → нет обучения.

---

### 4.4 Learning Layer (L4)

**Сценарии:**
- повтор OutcomeAppliedToLearning
- conflicting outcomes
- origin_type ≠ system

**Поведение:**
- повтор learning запрещён
- user-origin outcomes игнорируются
- конфликт → abort

**Retry:**  
❌ **Нет**

**Safe Default:**  
Learning не происходит.

---

## 5. Retry / No-Retry Matrix

| Сценарий | Retry |
|----------|-------|
| Raw metrics ingestion | ✅ |
| Daily snapshot creation | ✅ |
| Outcome aggregation | ❌ |
| Learning update | ❌ |
| Decision execution | ❌ |

---

## 6. Idempotency Enforcement

**Критические неидемпотентные операции:**
- OutcomeAppliedToLearning

**Для них:**
- повтор = hard abort
- никаких "best effort"

---

## 7. Partial Failure Semantics

**Если pipeline прервался:**
```
Raw → Snapshot → (FAIL) → Outcome
```

**Поведение:**
- уже созданные snapshot'ы остаются
- окно может быть закрыто позже
- learning не происходит

**Никакой rollback истории не допускается.**

---

## 8. Silent Failure Rule (важно)

**Система НЕ обязана:**
- объяснять пользователю, почему learning не произошёл
- репортить "фб ныл"
- интерпретировать environment как причину

**Внутреннее поведение ≠ пользовательское объяснение.**

---

## 9. Forbidden Error Handling Patterns

**Запрещено:**
- компенсировать отсутствие данных домыслами
- "достраивать" snapshot
- обучаться на частичном окне
- ретраить learning
- откатывать learning

---

## 10. Observability Principle (без реализации)

**Система обязана:**
- логировать причины abort
- различать:
  - no data
  - no window
  - no learning
- сохранять audit trail

**Но:**
observability не влияет на поведение системы.

---

## 11. Final Rule (жёсткое)

**Никакая ошибка не имеет права изменить знания системы.**

---

## 12. Layer Boundary Notice

Этот документ:
- завершает Error Handling-часть Layer 3,
- не описывает инфраструктурные ошибки (сеть, БД, очереди),
- не содержит retry-механик конкретных технологий.
