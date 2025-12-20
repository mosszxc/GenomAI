# Service Boundaries Specification
## GenomAI — Service Boundaries & Responsibilities (Layer 3)

**Версия:** v1.0  
**Статус:** CANONICAL / LAYER 3  
**Приоритет:** Критический  
**Основан на:** SYSTEM_ARCHITECTURE, ENTITY_LIFECYCLE, DATA_FLOW, MVP_SCOPE

---

## 1. Purpose

Данный документ фиксирует набор логических сервисов системы GenomAI, их зоны ответственности, и жёсткие границы допустимого поведения.

**Цель документа:**
- исключить дублирование логики,
- предотвратить утечки ответственности,
- сделать реализацию механическим отражением архитектуры.

**Документ:**
- не описывает инфраструктуру,
- не описывает технологии,
- не описывает API или протоколы.

---

## 2. Core Boundary Principle

**Сервис знает только то, что ему архитектурно разрешено знать, и делает только то, за что он единолично отвечает.**

**Ни один сервис:**
- не принимает решений вне своей зоны,
- не модифицирует чужие сущности,
- не интерпретирует данные, если он не их владелец.

---

## 3. Service Overview (Logical)

| Service | Тип | Назначение |
|---------|-----|------------|
| Ingestion Service | Stateless | Приём внешних данных |
| Validation Service | Stateless | Проверка контрактов |
| Transcription Service | Stateful | Генерация транскриптов |
| Decomposition Service | Stateless | Структурирование текста |
| Idea Registry Service | Stateful | Управление Idea |
| Decision Engine Service | Stateless | Принятие решений |
| Hypothesis Factory Service | Stateless | Генерация гипотез |
| Outcome Ingestion Service | Stateless | Приём performance |
| Learning Loop Service | Stateful | Обновление памяти |
| Memory Store Service | Stateful | Хранение знаний |

---

## 4. Service Definitions

### 4.1 Ingestion Service

**Тип:** Stateless

**Отвечает за:**
- приём `video_url`, `tracker_id`
- приём performance-фактов
- базовую маршрутизацию входа

**Не имеет права:**
- валидировать данные,
- интерпретировать вход,
- создавать сущности Layer 1.

---

### 4.2 Validation Service

**Тип:** Stateless

**Отвечает за:**
- Data Contract validation
- Input Normalization checks

**Поведение:**
- invalid input → reject
- valid input → pass through

**Не имеет права:**
- исправлять данные,
- запускать downstream-логику.

---

### 4.3 Transcription Service

**Тип:** Stateful

**Отвечает за:**
- автоматическую транскрипцию видео
- версионирование транскриптов
- статус доступности

**Гарантии:**
- один Creative → 1+ версии транскрипта
- транскрипт immutable после создания

**Критическое ограничение:**  
Транскрипт содержит **ТОЛЬКО текст того, что говорит лицо в ролике**.  
Визуалы, изображения, primary/description не обрабатываются.

**Не имеет права:**
- интерпретировать смысл,
- видеть Decision Engine,
- обучаться.

---

### 4.4 Decomposition Service

**Тип:** Stateless

**Отвечает за:**
- извлечение переменных Canonical Schema
- нормализацию значений enum
- формирование DecomposedCreative (schema-structured representation)

**Критическое правило терминологии:**
- **Creative = raw transcript (immutable)** — сырой транскрипт видео
- **DecomposedCreative = schema-structured representation** — структурированное представление по Canonical Schema
- **Никогда не называть DecomposedCreative просто "Creative"**

**Ограничения:**
- работает **только с текстом** (транскрипт видео),
- не видит performance,
- не знает source of truth,
- не принимает решений.

---

### 4.5 Idea Registry Service

**Тип:** Stateful

**Отвечает за:**
- создание Idea
- проверку identity (angle_type, core_belief, promise_type, state_transition, context_frame)
- дедупликацию
- cluster assignment (passive, получает от ML)

**Не имеет права:**
- удалять Idea,
- принимать решения,
- генерировать гипотезы.

---

### 4.6 Decision Engine Service

**Тип:** Stateless

**Отвечает за:**
- approve / reject / defer / allow_with_constraints
- формирование Decision Trace
- применение deterministic rules

**Ключевое правило:**  
**Единственный сервис, принимающий решения.**

**❗ КРИТИЧЕСКОЕ ПРАВИЛО ДЛЯ РЕАЛИЗАЦИИ:**

**Decision Engine is stateless across invocations.**

**It does not cache memory or decisions.**

**All required state is loaded per execution.**

**Детали:**
- Decision Engine читает:
  - Learning Memory (Confidence, Fatigue, Death)
  - Risk Budget / Fatigue
- Но **НЕ кеширует** эти данные между вызовами
- Но **НЕ хранит состояние** между вызовами
- Все требуемое состояние загружается **при каждом выполнении** (per execution)
- Каждый вызов Decision Engine начинается с "чистого листа"

**⚠️ Имплементационная ловушка:**
В n8n разработчик **НЕ должен**:
- ❌ кешировать результаты чтения Memory между вызовами Decision Engine
- ❌ хранить состояние Decision Engine между вызовами
- ❌ использовать глобальные переменные или shared state для Decision Engine
- ❌ полагаться на предыдущие результаты Decision Engine в текущем вызове

**Правильный подход:**
- ✅ При каждом вызове Decision Engine:
  - загрузить актуальное состояние Memory из Memory Store
  - загрузить актуальный Risk Budget / Fatigue
  - выполнить decision logic на основе загруженных данных
  - вернуть Decision без сохранения состояния
- ✅ Каждый вызов Decision Engine независим от предыдущих

**Защита от state drift:**
Это правило защищает от неявного state drift в n8n, когда кешированные данные могут стать устаревшими между вызовами.

**Не имеет права:**
- читать environment напрямую,
- видеть user-origin outcome,
- обучаться,
- использовать raw float ML signals (только buckets).

---

### 4.7 Hypothesis Factory Service

**Тип:** Stateless

**Отвечает за:**
- генерацию транскриптов
- соблюдение mutation scope
- привязку к Idea

**Критическое ограничение:**  
Генерирует **ТОЛЬКО транскрипты** (текст того, что говорит лицо в ролике).  
**НЕ генерирует:** визуалы, изображения, primary/description.

**Не имеет права:**
- менять Idea,
- влиять на Decision Engine,
- учитывать performance.

---

### 4.8 Outcome Ingestion Service

**Тип:** Stateless

**Отвечает за:**
- приём performance-фактов
- связывание с `tracker_id`
- маркировку `origin_type` (system | user)
- первичную валидацию

**Определение origin_type:**
- если `tracker_id` связан с Hypothesis → `origin_type = system`
- если `tracker_id` не связан с Hypothesis → `origin_type = user`

**Не имеет права:**
- интерпретировать результат,
- обновлять память.

---

### 4.9 Learning Loop Service

**Тип:** Stateful

**Отвечает за:**
- обновление confidence (с учётом environment weighting)
- fatigue updates
- idea death
- environment weighting
- разделение learning channels:
  - `system` outcome → causal updates
  - `user` outcome → observational memory

**Ключевое правило:**  
**Learning интерпретирует. Decision — нет.**

**Не имеет права:**
- изменять прошлые Decision,
- принимать решения,
- читать environment напрямую (использует environment_context из Outcome).

---

### 4.10 Memory Store Service

**Тип:** Stateful

**Отвечает за:**
- хранение memory-сущностей (Confidence, Fatigue, Death, Cluster)
- версионирование знаний
- append-only историю

**Не имеет права:**
- принимать решения,
- изменять прошлые факты,
- интерпретировать данные.

---

## 5. Allowed Service Interactions

```
Ingestion → Validation → Transcription
                     → Decomposition
Decomposition → Idea Registry → Decision Engine
Decision Engine → Hypothesis Factory
Outcome Ingestion → Learning Loop → Memory Store
```

**Любое иное взаимодействие — архитектурное нарушение.**

---

## 6. Forbidden Couplings (Critical)

**Запрещено:**
- Decision Engine ↔ Memory Store (write)
- Decomposition ↔ Outcome
- Hypothesis Factory ↔ Learning
- Ingestion ↔ Decision Engine
- Transcription ↔ Learning
- Decision Engine ↔ user-origin Outcome
- Decision Engine ↔ environment_context (read)

---

## 7. Stateless vs Stateful Rule

**Stateless сервисы:**
- могут быть переиспользованы,
- не хранят знания,
- не влияют на поведение системы во времени.

**Stateful сервисы:**
- единственный источник правды,
- меняют поведение системы,
- строго ограничены по ответственности.

---

## 8. Evolution Rule

**Добавление нового сервиса допустимо, если:**
- он не дублирует существующую ответственность,
- его роль нельзя выразить через текущие сервисы,
- он не нарушает Layer 0–1.

**Изменение ответственности сервиса:**
- требует новой версии документа,
- запрещено "по месту в коде".

---

## 9. Final Rule

**Если сервис знает больше, чем описано здесь — он спроектирован неверно.**
