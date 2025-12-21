# MVP Scope Specification
## GenomAI — Minimum Viable Product Scope

**Версия:** v1.0  
**Статус:** CANONICAL / PRE-IMPLEMENTATION  
**Приоритет:** Критический  
**Основан на:** Layer 0 (Doctrine), Layer 1 (Logical Architecture), Layer 2 (Product & Interaction)

---

## 1. Purpose

Данный документ фиксирует осознанный и ограниченный объём функциональности, который будет реализован в первой версии продукта (MVP).

**Цель MVP:**
- проверить работоспособность архитектуры на реальном рынке,
- получить первые реальные Outcome,
- избежать избыточной реализации.

**MVP Scope не меняет архитектуру и не вводит новых сущностей.**  
Он временно отключает часть возможностей, заложенных в системе.

---

## 2. Core MVP Principle

**MVP должен доказать, что система способна принимать решения и улучшаться от фактов рынка — даже в сильно урезанном виде.**

---

## 3. In-Scope (что ВХОДИТ в MVP)

### 3.1 Supported Inputs

**В MVP поддерживаются только следующие входы:**

- `video_url` — ссылка на видео-креатив
- `tracker_id` — идентификатор из Keitaro
- performance-факты:
  - spend
  - primary metric
  - time window

**❌ Ручные транскрипты не поддерживаются.**

**Критическое ограничение:**  
Система работает **ТОЛЬКО с транскриптом видео** (аудиочасть).  
Визуалы, изображения, primary/description не обрабатываются.

### 3.2 Transcription & Decomposition

**В MVP:**
- используется один воркфлоу транскрипции,
- одна версия Canonical Schema,
- одна модель decomposition (LLM).

**❌ Никакого A/B decomposition.**  
**❌ Никаких fallback-моделей.**

### 3.3 Decision Engine (MVP Mode)

**В MVP Decision Engine работает в упрощённом режиме:**

- один горизонт (T1)
- базовые checks:
  - duplicate
  - hard constraints
  - simple fatigue
- **без:**
  - epistemic shock
  - regime transition
  - стратегических приоров

**Критическое правило:**  
Decision Engine работает **ТОЛЬКО с bucket-значениями**, не с raw float.

**⚠️ Важное уточнение для реализации:**
В MVP используется только **HARD_DEAD без resurrection**.  
SOFT_DEAD и уровни death используются только в full system.

### 3.4 Hypothesis Generation

**В MVP:**
- 1–3 транскрипта на одну APPROVED Idea
- фиксированный mutation scope
- без адаптивного количества вариантов

**Критическое ограничение:**  
Транскрипты содержат **ТОЛЬКО текст того, что говорит лицо в ролике**.  
**НЕ содержат:** визуалы, изображения, primary/description.

### 3.5 Learning Loop (Minimal)

**В MVP Learning Loop обновляет только:**
- basic confidence (binary / coarse) — на основе CPA_window
- simple fatigue — на основе динамики CPA_window
- idea death (hard threshold) — на основе CPA_window

**❗ КРИТИЧЕСКОЕ ПРАВИЛО:**

**Единственная метрика успешности:** `CPA_window`

**Формула:** `CPA_window = total_spend(window) / total_conversions(window)`

**Окно:** фиксированное агрегированное окно (D1–D3 или D1–D7, выбрать одно и использовать везде)

**Применяется только к System Outcome.**

**❌ Нет:**
- сложного decay
- cluster priors
- long-term memory
- multi-metric optimization
- использования CTR, CVR, ROAS для learning

### 3.6 Telegram Interaction

**В MVP:**
- только push-модель
- только текстовые сообщения
- без inline-команд
- без кнопок
- без истории диалога

### 3.7 User Roles

**В MVP:**
- один тип пользователя — Media Buyer
- без ролей
- без override
- без прав доступа

---

## 4. Explicitly Out of Scope (что НЕ входит)

Следующее осознанно исключено из MVP, даже если описано в архитектуре:

### 4.1 Advanced System Modes

- epistemic shock
- recovery mode
- regime transition

### 4.2 Multi-Horizon Logic

- T2 / T3
- стратегические горизонты
- долгосрочные эффекты

### 4.3 Advanced ML Signals

- similarity embeddings
- novelty scoring
- cluster dynamics
- fatigue predictors

**Примечание:**  
В MVP ML-сигналы могут быть упрощены или эмулированы правилами.

### 4.4 Human Override

- любые формы ручного вмешательства
- override governance
- exception handling человеком

### 4.5 Scaling & Multi-Tenancy

- несколько вертикалей
- несколько источников трафика
- tenant isolation

### 4.6 Analytics & Dashboards

- визуализация метрик
- аналитические отчёты
- админ-панели

---

## 5. MVP Success Criteria

**❗ КРИТИЧЕСКОЕ ПРАВИЛО — MVP SUCCESS METRIC:**

**В рамках MVP единственной метрикой успешности является CPA_window, рассчитанный по агрегированному временному окну и применимый исключительно к System Outcome.**

**Single Success Metric:** `CPA_window`

**Отсутствие multi-metric optimization:**
- ❌ CTR не используется для learning/decision
- ❌ CVR не используется для learning/decision
- ❌ ROAS не используется для learning/decision
- ❌ Early CPA не используется для learning/decision
- ❌ Engagement metrics не используются для learning/decision

**Rule-based only, no ML optimism:**
- Learning основан на простых правилах (например, leads > 0 → +1 confidence)
- Нет сложных ML-моделей для оптимизации
- Нет multi-objective optimization

**MVP считается успешным, если:**

### Система:
- корректно принимает video_url + tracker_id
- стабильно транскрибирует
- принимает детерминированные решения
- рассчитывает CPA_window для System Outcome

### Пользователь:
- получает новые транскрипты
- может их запускать
- может возвращать performance

### Learning:
- меняет поведение системы со временем на основе CPA_window
- не деградирует
- не требует ручной правки
- использует только CPA_window как метрику успешности

---

## 6. MVP Failure Signals

**MVP считается проблемным, если:**
- система требует ручных «подталкиваний»
- Decision Engine приходится «объяснять»
- без интерпретаций нельзя понять, что делать
- система генерирует тексты без решений
- обучение происходит «на ощущениях»

---

## 7. Non-Goals (важно зафиксировать)

**MVP НЕ предназначен для:**
- максимизации ROI
- автоматического масштабирования
- замены медиабайера
- доказательства «качества текста»

**MVP предназначен для:**
- проверки архитектуры в бою.

---

## 8. Evolution Rule

**Любое расширение MVP:**
- происходит после получения реальных Outcome,
- оформляется новой версией Scope,
- не ломает Layer 0–1.

---

## 9. Exit Criteria (когда MVP завершён)

**MVP считается завершённым, когда:**
- накоплено N реальных Outcome,
- система хотя бы один раз:
  - убила идею,
  - сменила поведение,
  - перестала выдавать транскрипты из-за fatigue.

---

## 10. Final Rule

**Если в MVP появляется функция, которую нельзя обосновать получением Outcome — она лишняя.**
