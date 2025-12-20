# 06_telegram_output_playbook.md

**STEP 06 — Telegram Output (MVP)**

**Статус:** IMPLEMENTATION PLAYBOOK  
**Scope:** MVP  
**Зависимости:**
- `05_hypothesis_factory_playbook.md` (Hypotheses сгенерированы)

**Следующий шаг:** `07_outcome_ingestion_playbook.md`

## 0. Назначение шага

Этот шаг доставляет ценность пользователю.

Telegram — **витрина, не интерфейс управления**.

Пользователь получает результат, но не управляет системой.

## 1. Входные данные

### 1.1 Источник

- событие `HypothesisGenerated`

### 1.2 Контракт входа

```json
{
  "idea_id": "uuid",
  "decision_id": "uuid",
  "count": 3
}
```

## 2. n8n Workflow

**Workflow name:** `telegram_hypothesis_delivery`

### 2.1 Trigger

- **Node:** Event Trigger
- **Event:** `HypothesisGenerated`

### 2.2 Load Hypotheses

- **Node:** Supabase Select

```sql
SELECT id, content
FROM hypotheses
WHERE idea_id = :idea_id
  AND decision_id = :decision_id
ORDER BY created_at ASC;
```

📌 **Порядок фиксированный, без сортировки "по качеству".**

### 2.3 Message Assembly (Deterministic)

- **Node:** Function

**Правила:**
- формат сообщения фиксирован
- без CTA
- без объяснений
- без "почему"

**Пример формата:**
```
Hypotheses for Idea #<short_id>

1) <text>
2) <text>
3) <text>
```

📌 **Никакой логики в тексте.**

### 2.4 Send Telegram Message

- **Node:** Telegram Send Message
- `chat_id` — конфиг
- `parse_mode` — plain text / markdown
- `disable_web_page_preview` — true

### 2.5 Persist Delivery

- **Node:** Supabase Insert
- **Таблица:** `deliveries`

**Поля:**
- `id` (uuid)
- `idea_id`
- `decision_id`
- `channel = 'telegram'`
- `status = 'sent'`
- `sent_at`

### 2.6 Emit Event

**HypothesisDelivered**

```json
{
  "idea_id": "uuid",
  "decision_id": "uuid",
  "channel": "telegram"
}
```

## 3. Хранилище

### Таблица deliveries

```sql
deliveries (
  id           uuid primary key,
  idea_id      uuid not null,
  decision_id  uuid not null,
  channel      text not null,
  status       text not null,
  sent_at      timestamp not null
)
```

### Инварианты

- append-only
- UPDATE / DELETE запрещены
- delivery ≠ confirmation

## 4. События

**Обязательные:**

### HypothesisDelivered

```json
{
  "idea_id": "uuid",
  "decision_id": "uuid",
  "channel": "telegram"
}
```

**Запрещённые:**

- любые user feedback events
- любые interaction events

## 5. Definition of Done (DoD)

Шаг считается выполненным, если:
- ✅ сообщение отправляется в Telegram
- ✅ сообщение содержит все гипотезы
- ✅ delivery сохраняется
- ✅ событие `HypothesisDelivered` эмитится
- ✅ нет интерактива

## 6. Типовые ошибки (PR-блокеры)

❌ **кнопки / inline keyboard**  
❌ **вопросы пользователю**  
❌ **"оцените гипотезу"**  
❌ **логика "если длинно — сократить"**  
❌ **зависимость от user input**

## 7. Ручные проверки (обязательные)

### Check 1 — Happy path
- HypothesisGenerated → сообщение в Telegram
- delivery сохранён

### Check 2 — Content integrity
- все гипотезы присутствуют
- порядок соответствует insertion order

### Check 3 — No interaction
- на сообщение нельзя ответить логикой системы

## 8. Выход шага

На выходе гарантировано:

**Пользователь получил результат,**
**но не повлиял на систему.**

## 9. Жёсткие запреты

❌ интерактив  
❌ feedback  
❌ управление системой  
❌ ручные триггеры

## 10. Готовность к следующему шагу

Можно переходить к `07_outcome_ingestion_playbook.md`, если:
- ✅ сообщения стабильно отправляются
- ✅ формат детерминирован
- ✅ нет скрытого интерактива
