# STEP 07 - Outcome Ingestion Issues

## Epic #7: STEP 07 - Outcome Ingestion (MVP)

**Описание:**
Реализация outcome ingestion для получения метрик из Keitaro API и сохранения их в БД.

**Статус:** В работе

**Workflow:** `Outcome Ingestion Keitaro` (ID: `zMHVFT2rM7PpTiJj`)

**Playbook:** `docs/layer-4-implementation-planning/STEP_IMPLEMENTATION_PLAYBOOKS/07_outcome_ingestion_playbook.md`

**Зависимости:**
- STEP 06 (telegram_output_playbook) - hypotheses доставлены

**Следующий шаг:** STEP 08 (learning_loop_playbook)

---

## Issue 1: Тестирование workflow Outcome Ingestion Keitaro

**Тип:** Task  
**Epic:** #7  
**Приоритет:** High

**Описание:**
Протестировать workflow `Outcome Ingestion Keitaro` (ID: `zMHVFT2rM7PpTiJj`) и убедиться, что все узлы работают корректно.

**Чеклист:**
- [ ] Запустить workflow через Manual Trigger
- [ ] Проверить, что все узлы выполняются без ошибок
- [ ] Проверить, что данные корректно передаются между узлами
- [ ] Проверить, что SplitInBatches connections правильные (output 1 для loop, output 0 для done)
- [ ] Проверить, что обработка ошибок работает (пропуск кампаний без данных)
- [ ] Проверить, что события эмитятся корректно

**Ожидаемый результат:**
- Workflow выполняется без ошибок
- Все узлы работают корректно
- Данные передаются между узлами правильно

**Связанные файлы:**
- `docs/layer-4-implementation-planning/STEP_IMPLEMENTATION_PLAYBOOKS/07_outcome_ingestion_playbook.md`

---

## Issue 2: Проверка данных в БД после выполнения workflow

**Тип:** Task  
**Epic:** #7  
**Приоритет:** High

**Описание:**
Проверить, что данные корректно сохраняются в БД после выполнения workflow.

**Чеклист:**
- [ ] Проверить таблицу `genomai.raw_metrics_current`:
  - [ ] Записи создаются/обновляются для каждого `tracker_id`
  - [ ] Поле `date` содержит вчерашнюю дату
  - [ ] Поле `metrics` содержит корректные данные (clicks, conversions, revenue, cost)
  - [ ] Поле `updated_at` обновляется при изменении
- [ ] Проверить таблицу `genomai.daily_metrics_snapshot`:
  - [ ] Snapshot создается для каждого `tracker_id` с данными
  - [ ] Поле `date` содержит вчерашнюю дату
  - [ ] Поле `metrics` содержит корректные данные
  - [ ] Unique constraint `(tracker_id, date)` работает (нет дубликатов)
- [ ] Проверить таблицу `genomai.event_log`:
  - [ ] Событие `RawMetricsObserved` создается после сохранения raw metrics
  - [ ] Событие `DailyMetricsSnapshotCreated` создается после создания snapshot
  - [ ] Payload событий содержит корректные данные

**Запросы для проверки:**
```sql
-- Проверить raw_metrics_current
SELECT tracker_id, date, metrics, updated_at 
FROM genomai.raw_metrics_current 
ORDER BY updated_at DESC 
LIMIT 10;

-- Проверить daily_metrics_snapshot
SELECT tracker_id, date, metrics, created_at 
FROM genomai.daily_metrics_snapshot 
ORDER BY created_at DESC 
LIMIT 10;

-- Проверить события
SELECT event_type, entity_type, entity_id, payload, occurred_at 
FROM genomai.event_log 
WHERE event_type IN ('RawMetricsObserved', 'DailyMetricsSnapshotCreated')
ORDER BY occurred_at DESC 
LIMIT 10;
```

**Ожидаемый результат:**
- Данные корректно сохраняются в БД
- Все таблицы содержат ожидаемые данные
- События эмитятся корректно

---

## Issue 3: Валидация соответствия playbook и проверка ручных тестов

**Тип:** Task  
**Epic:** #7  
**Приоритет:** Medium

**Описание:**
Проверить, что workflow соответствует playbook и пройти все ручные проверки.

**Чеклист согласно playbook:**

### Check 1 — Happy path
- [ ] Schedule Trigger работает (cron: `0 3 * * *`)
- [ ] Workflow выполняется автоматически
- [ ] Snapshot появляется в `daily_metrics_snapshot`
- [ ] Raw metrics обновляются в `raw_metrics_current`

### Check 2 — Missing data
- [ ] Keitaro вернул пустой ответ для некоторых кампаний
- [ ] Workflow не падает при отсутствии данных
- [ ] Кампании без данных пропускаются корректно
- [ ] Workflow продолжает обработку других кампаний

### Check 3 — Retry safety
- [ ] Повторный запуск workflow (через cron или manual trigger)
- [ ] Duplicate snapshot не создается (unique constraint работает)
- [ ] Raw metrics обновляются корректно при повторном запуске
- [ ] Idempotency работает (можно запускать несколько раз без дубликатов)

**Проверка соответствия playbook:**
- [ ] Workflow соответствует структуре из playbook
- [ ] Все узлы реализованы согласно playbook
- [ ] События эмитятся согласно playbook
- [ ] Нет запрещенных действий (learning, интерпретация, оптимизация, decision)

**Ожидаемый результат:**
- Все проверки из playbook пройдены
- Workflow соответствует playbook
- Готовность к переходу к STEP 08

---

## Issue 4: Проверка конфигурации Keitaro

**Тип:** Task  
**Epic:** #7  
**Приоритет:** Medium

**Описание:**
Проверить, что конфигурация Keitaro настроена корректно в БД.

**Чеклист:**
- [ ] Проверить таблицу `genomai.keitaro_config`:
  - [ ] Есть активная конфигурация (`is_active = true`)
  - [ ] Поле `domain` содержит корректный URL Keitaro
  - [ ] Поле `api_key` содержит корректный API ключ
  - [ ] Только одна активная конфигурация существует
- [ ] Проверить, что workflow корректно загружает конфигурацию
- [ ] Проверить, что API запросы к Keitaro используют правильные credentials

**Запросы для проверки:**
```sql
-- Проверить конфигурацию
SELECT id, domain, is_active, created_at, updated_at 
FROM genomai.keitaro_config 
WHERE is_active = true;
```

**Ожидаемый результат:**
- Конфигурация настроена корректно
- Workflow корректно загружает конфигурацию
- API запросы к Keitaro работают

---

## Definition of Done (DoD)

STEP 07 считается выполненным, если:
- ✅ Workflow создан и настроен
- ✅ Workflow протестирован и работает без ошибок
- ✅ Данные корректно сохраняются в БД
- ✅ Все проверки из playbook пройдены
- ✅ Raw metrics подтягиваются по cron
- ✅ Daily snapshot создаётся
- ✅ События эмитятся
- ✅ Нет запрещенных действий (learning, интерпретация, оптимизация, decision)

