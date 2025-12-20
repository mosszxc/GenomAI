# Input Normalization Specification
## GenomAI — Input Normalization & Ingestion Rules (Layer 2)

**Версия:** v1.0  
**Статус:** CANONICAL / LAYER 2  
**Приоритет:** Высокий  
**Основан на:** Usage Doctrine, DATA_FLOW, TELEGRAM_INTERACTION_MODEL, Data Contracts

---

## 1. Purpose

Данный документ определяет какие входные данные считаются допустимыми, как они нормализуются перед входом в Layer 1, и какие минимальные условия должны быть выполнены, чтобы данные существовали для системы.

Документ:
- описывает продуктовый вход, а не внутренние сущности,
- не описывает реализацию транскрипции,
- не описывает Decision Engine или обучение.

---

## 2. Core Principle

**Система принимает ссылки и факты, а не подготовленные человеком данные.**

**Media Buyer не обязан:**
- делать транскрипцию,
- чистить текст,
- размечать креатив.

---

## 3. Supported Input Types

### 3.1 Creative Video Reference (Primary)

**Основной вход для креатива.**

**Media Buyer передаёт:**
- `video_url` — ссылка на видео-креатив
- `tracker_id` — идентификатор из системы трекинга (Keitaro)

**Это единственный обязательный способ регистрации нового креатива.**

**Критическое ограничение:**  
Система работает **ТОЛЬКО с транскриптом видео** (аудиочасть).  
Визуалы, изображения, primary/description в Facebook Ads не обрабатываются.

### 3.2 Performance Outcome Reference

**Для обучения Media Buyer передаёт:**
- `tracker_id`
- performance-факты (spend, metric, time window)

**Связь Outcome ↔ Creative происходит через tracker_id, а не через текст или видео.**

**Определение origin_type:**
- Если `tracker_id` связан с Hypothesis (system-generated creative) → `origin_type = system`
- Если `tracker_id` не связан с Hypothesis (user-generated creative) → `origin_type = user`
- Это влияет на то, как Outcome используется в Learning Loop:
  - `system` → causal updates (обновление confidence, fatigue, death memory)
  - `user` → observational memory (расширение пространства идей, без causal updates)

### 3.3 Optional Environment Signals

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

## 4. Creative Registration Semantics

### 4.1 What Is Considered a Creative

**Creative считается зарегистрированным, если:**
- получен `video_url`,
- получен `tracker_id`,
- ссылка доступна для обработки.

**Creative не требует ручного описания.**

### 4.2 Tracker ID Role

**tracker_id:**
- является внешним идентификатором,
- не несёт бизнес-логики,
- используется для:
  - связывания Creative ↔ Outcome,
  - дедупликации,
  - временной корреляции.

**Система не интерпретирует tracker_id.**

---

## 5. Transcription Workflow Boundary

### 5.1 Automated Transcription

- транскрипция выполняется автоматически системой,
- Media Buyer **никогда не присылает транскрипт вручную**,
- транскрипт считается производным артефактом.

**Критическое ограничение:**  
Транскрипт содержит **ТОЛЬКО текст того, что говорит лицо в ролике**.  
Визуальные элементы, primary/description не включаются.

### 5.2 Transcription Failure

**Если транскрипция невозможна:**
- Creative помечается как `invalid`,
- пользователь уведомляется (System Notification),
- дальнейшая обработка не происходит,
- состояние системы не изменяется.

---

## 6. Normalization Steps (Logical)

После получения входа система логически выполняет:

1. **Проверку доступности видео**
   - video_url должен быть доступен
   - формат должен поддерживаться

2. **Проверку наличия tracker_id**
   - tracker_id обязателен
   - отсутствие → input reject

3. **Создание Creative reference**
   - создаётся сущность Creative с video_url и tracker_id
   - Creative помечается как `pending_transcription`

4. **Запуск transcription workflow**
   - автоматическая транскрипция видео
   - извлечение **ТОЛЬКО аудиочасти** (текст речи)

5. **Валидацию результата транскрипции**
   - транскрипт должен быть непустым
   - транскрипт передаётся в Validation Layer (Layer 1)

**Только после этого данные допускаются в Layer 1.**

---

## 7. Forbidden Input Patterns

**Архитектурно запрещено:**
- отправка ручного транскрипта
- отправка частичного текста
- отправка «улучшенной версии» текста
- регистрация Creative без tracker_id
- подмена tracker_id задним числом
- отправка визуалов, изображений, primary/description

**Любая из этих попыток → input reject.**

---

## 8. Edge Cases & Clarifications

- **Один tracker_id → один Creative**
  - Повторная отправка того же tracker_id → дедупликация

- **Один Creative → один транскрипт (версии допустимы)**
  - При обновлении схемы транскрипт может быть пересобран
  - Исторические версии архивируются

- **Изменение видео по той же ссылке → новый Creative**
  - Если video_url изменился (новое видео), создаётся новый Creative
  - Если video_url тот же, но содержимое изменилось, система может создать новый Creative

- **Повторная отправка той же ссылки → дедупликация**
  - Система проверяет существование Creative по video_url + tracker_id
  - Дубликаты не создаются

---

## 9. Error Feedback Semantics

**При ошибках система отправляет:**
- тип ошибки:
  - `missing_tracker_id` — отсутствует обязательный tracker_id
  - `inaccessible_video` — видео недоступно
  - `transcription_failure` — транскрипция не удалась
  - `invalid_format` — неподдерживаемый формат
- факт отказа,
- отсутствие изменений в системе.

**Fail-safe стратегия:**  
Лучше не принять вход, чем принять неверный.

---

## 10. Security & Trust Model

- `video_url` не считается trusted content,
- `tracker_id` не считается trusted identifier,
- доверие возникает только после Outcome validation.

**Все входные данные валидируются через Data Contracts (Layer 1).**

---

## 11. Evolution Rule

**Изменение входных правил допустимо, если:**
- не нарушает DATA_FLOW,
- не ломает Entity Lifecycle,
- не вводит ручную подготовку данных,
- не нарушает Usage Doctrine.

**Любые изменения требуют:**
- новой версии документа,
- обратной совместимости по смыслу,
- обновления Data Contracts (Layer 1).

---

## 12. Layer Boundary Notice

Этот документ:
- принадлежит Layer 2 (Product & Interaction),
- описывает вход до Layer 1,
- не влияет на Decision Engine или Learning напрямую.

---

## 13. Final Rule

**Media Buyer передаёт ссылки и факты.**  
**Система берёт на себя всё остальное.**
