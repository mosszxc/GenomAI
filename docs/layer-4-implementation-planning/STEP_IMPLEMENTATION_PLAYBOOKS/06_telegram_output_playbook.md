# 06_telegram_output_playbook.md

**STEP 06 — Telegram Output (MVP)**

**Статус:** IMPLEMENTED
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

- После Decision Engine APPROVE
- Гипотезы сгенерированы в `CreativePipelineWorkflow`

### 1.2 Контракт входа

```json
{
  "idea_id": "uuid",
  "decision_id": "uuid",
  "buyer_id": "uuid",
  "hypotheses": [{"id": "uuid", "content": "string"}]
}
```

## 2. Реализация (Temporal)

**Workflow:** `CreativePipelineWorkflow` (Step 7)
**Файл:** `temporal/workflows/creative_pipeline.py` (строки 290-324)

### 2.1 Trigger

Автоматически после генерации гипотез (Step 6 в workflow)

### 2.2 Get Buyer Chat ID

**Activity:** `get_buyer_chat_id`

```python
chat_id = await workflow.execute_activity(
    get_buyer_chat_id,
    input.buyer_id,
    ...
)
```

### 2.3 Send Telegram Message

**Activity:** `send_hypothesis_to_telegram`

```python
delivery_result = await workflow.execute_activity(
    send_hypothesis_to_telegram,
    hypothesis_id,
    hypothesis_content,
    chat_id,
    idea_id,
    ...
)
```

### 2.4 Persist Delivery

Записывается в `genomai.deliveries`:
- `id` (uuid)
- `idea_id`
- `hypothesis_id`
- `channel = 'telegram'`
- `status = 'sent'`
- `sent_at`

### 2.5 Emit Event

**Activity:** `emit_delivery_event`

Event: `HypothesisDeliverySuccess` или `HypothesisDeliveryFailed`

## 3. Activities

**Файл:** `temporal/activities/telegram.py`

| Activity | Назначение |
|----------|-----------|
| `send_hypothesis_to_telegram` | Отправка сообщения в Telegram |
| `get_buyer_chat_id` | Получение chat_id из buyers таблицы |
| `update_hypothesis_delivery_status` | Обновление статуса доставки |
| `emit_delivery_event` | Эмиссия события в event_log |

## 4. Хранилище

### Таблица deliveries

```sql
deliveries (
  id           uuid primary key,
  idea_id      uuid not null,
  hypothesis_id uuid,
  channel      text not null,
  status       text not null,
  sent_at      timestamp not null
)
```

### Инварианты

- append-only
- UPDATE / DELETE запрещены
- delivery ≠ confirmation

## 5. События

**Обязательные:**

### HypothesisDeliverySuccess

```json
{
  "idea_id": "uuid",
  "hypothesis_id": "uuid",
  "channel": "telegram",
  "chat_id": "string"
}
```

**Запрещённые:**

- любые user feedback events
- любые interaction events

## 6. Definition of Done (DoD)

Шаг считается выполненным, если:
- ✅ сообщение отправляется в Telegram
- ✅ сообщение содержит гипотезу
- ✅ delivery сохраняется в БД
- ✅ событие эмитится в event_log
- ✅ нет интерактива

## 7. Типовые ошибки (PR-блокеры)

❌ **кнопки / inline keyboard**
❌ **вопросы пользователю**
❌ **"оцените гипотезу"**
❌ **логика "если длинно — сократить"**
❌ **зависимость от user input**

## 8. Ручные проверки (обязательные)

### Check 1 — Happy path
- CreativePipeline APPROVE → сообщение в Telegram
- delivery сохранён

### Check 2 — Content integrity
- гипотеза присутствует
- buyer получил сообщение

### Check 3 — No interaction
- на сообщение нельзя ответить логикой системы

## 9. Выход шага

На выходе гарантировано:

**Пользователь получил результат,**
**но не повлиял на систему.**

## 10. Жёсткие запреты

❌ интерактив
❌ feedback
❌ управление системой
❌ ручные триггеры

## 11. Готовность к следующему шагу

Можно переходить к `07_outcome_ingestion_playbook.md`, если:
- ✅ сообщения стабильно отправляются
- ✅ формат детерминирован
- ✅ нет скрытого интерактива
