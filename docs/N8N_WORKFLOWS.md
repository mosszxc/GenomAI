# n8n Workflows Reference

## Overview

GenomAI использует 23 активных workflow для оркестрации пайплайна. Все workflow следуют event-driven архитектуре с emit событий в Supabase.

**Последнее обновление:** 2025-12-26
**Статус:** 23/23 OPERATIONAL

## E2E Test Results (2025-12-26)

| Workflow | Status | Notes |
|----------|--------|-------|
| keep_alive_decision_engine | ✅ PASSED | Health check OK |
| decision_engine_mvp | ✅ PASSED | APPROVE, all checks passed |
| idea_registry_create | ✅ PASSED | New idea created |
| creative_decomposition_llm | ✅ PASSED | Transcript + decomposed created |
| hypothesis_factory_generate | ✅ PASSED | Hypothesis created, LLM generation works |
| Telegram Hypothesis Delivery | ✅ PASSED | Message sent, hypothesis updated |
| Keitaro Poller | ✅ PASSED | Metrics collected from API |
| Learning Loop v2 | ✅ PASSED | Confidence versioning works |
| Telegram Router | ✅ PASSED | /help always works (#119), routing fixed |

## Workflow Index

| ID | Name | Trigger | Purpose | Active | Tested |
|----|------|---------|---------|--------|--------|
| `BuyQncnHNb7ulL6z` | Telegram Router | Telegram | Маршрутизация Telegram сообщений | ✅ | ✅ #119 |
| `hgTozRQFwh4GLM0z` | Buyer Onboarding | Telegram | Онбординг новых байеров + Historical Import | ✅ | ✅ #97 |
| `d5i9dB2GNqsbfmSD` | Buyer Creative Registration | Telegram | Регистрация креативов от байеров | ✅ | ✅ #97 |
| `rHuT8dYyIXoiHMAV` | Buyer Stats Command | Telegram | Команда /stats для байеров | ✅ | ✅ #97 |
| `WkS1fPSxZaLmWcYy` | Buyer Daily Digest | Schedule | Ежедневный отчет байерам | ✅ | ✅ #97 |
| `4uluD04qYHhsetBy` | Buyer Test Conclusion Checker | Webhook | Проверка завершения тестов | ✅ | ✅ #97 |
| `WMnFHqsFh8i7ddjV` | GenomAI - Creative Transcription | Webhook | Транскрипция видео через AssemblyAI | ✅ | ✅ #93 |
| `mv6diVtqnuwr7qev` | creative_decomposition_llm | Webhook | LLM декомпозиция креативов | ✅ | ✅ #93 |
| `cGSyJPROrkqLVHZP` | idea_registry_create | Webhook | Создание идей из креативов | ✅ | ✅ #94 |
| `YT2d7z5h9bPy1R4v` | decision_engine_mvp | Webhook/Manual | Вызов Decision Engine API | ✅ | ✅ #95 |
| `ClXUPP2IvWRgu99y` | keep_alive_decision_engine | Schedule | Keep-alive для DE (Issue #91) | ✅ | ✅ #101 |
| `oxG1DqxtkTGCqLZi` | hypothesis_factory_generate | Webhook | Генерация гипотез через LLM | ✅ | ✅ #96 |
| `5q3mshC9HRPpL6C0` | Telegram Hypothesis Delivery | Webhook | Доставка гипотез в Telegram | ✅ | ✅ E2E |
| `0TrVJOtHiNEEAsTN` | Keitaro Poller | Schedule/Webhook | Сбор метрик из Keitaro | ✅ | ✅ #98 |
| `Gii8l2XwnX43Wqr4` | Snapshot Creator | Webhook | Создание daily snapshots | ✅ | ✅ #98 |
| `bbbQC4Aua5E3SYSK` | Outcome Processor | Webhook | Обработка outcomes, вызов DE | ✅ | ✅ #98 |
| `243QnGrUSDtXLjqU` | Outcome Aggregator | Webhook | Агрегация outcomes для Learning Loop | ✅ | ✅ #98 |
| `fzXkoG805jQZUR3S` | Learning Loop v2 | Webhook | Обновление scores идей | ✅ | ✅ #98 |
| `1FC7amTd3dCRZPEa` | Historical Creative Import | Webhook | Импорт исторических креативов | ✅ | ✅ #100 |
| `lmiWkYTRZPSpydJH` | Buyer Historical Loader | Webhook | Загрузка campaigns из Keitaro для buyer | ✅ | ✅ #100 |
| `A8gKvO5810L1lusZ` | Buyer Historical URL Handler | Telegram | Обработка video_url от buyer в onboarding | ✅ | ✅ #100 |
| `UYgvqpsU3TMzb2Qd` | Historical Import Video Handler | Telegram | Обработка video_url из Telegram | ✅ | ✅ #100 |
| `dvZvUUmhtPzYOK7X` | creative_ingestion_webhook | Webhook | Legacy (заменён Buyer Creative Registration) | ❌ | - |

---

## 1. creative_ingestion_webhook

**ID:** `dvZvUUmhtPzYOK7X`
**Nodes:** 15
**Active:** ❌ No (заменён на Buyer Creative Registration)

### Purpose
Входная точка для регистрации креативов. Валидирует схему, проверяет идемпотентность, создает креатив и вызывает decomposition.

### Flow
```
Webhook Trigger → Schema Validation → Validation Check
  ├─ [INVALID] → Emit CreativeIngestionRejected → Error Response
  └─ [VALID] → Emit CreativeReferenceReceived → Idempotency Check → Creative Found?
                 ├─ [EXISTS] → Emit CreativeRegistered (Existing) → Success Response
                 └─ [NEW] → Create Creative → Emit CreativeRegistered (New) → Call Decomposition → Success Response
```

### Nodes
| ID | Name | Type |
|----|------|------|
| `webhook-trigger` | Webhook Trigger | webhook |
| `schema-validation` | Schema Validation | function |
| `validation-check` | Validation Check | if |
| `emit-rejected-event` | Emit CreativeIngestionRejected | supabase |
| `error-response` | Error Response | respondToWebhook |
| `emit-reference-received` | Emit CreativeReferenceReceived | supabase |
| `idempotency-check` | Idempotency Check | supabase |
| `creative-found-check` | Creative Found? | if |
| `emit-registered-existing` | Emit CreativeRegistered (Existing) | supabase |
| `create-creative` | Create Creative | supabase |
| `emit-registered-new` | Emit CreativeRegistered (New) | supabase |
| `call-decomposition` | Call Decomposition | httpRequest |
| `success-response` | Success Response | respondToWebhook |

### Events Emitted
- `CreativeIngestionRejected` - при ошибке валидации
- `CreativeReferenceReceived` - при получении валидного креатива
- `CreativeRegistered` - при успешной регистрации

---

## 2. idea_registry_create

**ID:** `cGSyJPROrkqLVHZP`
**Nodes:** 11
**Active:** Yes

### Purpose
Создает идеи из decomposed креативов. Генерирует canonical hash для идемпотентности, вызывает Decision Engine.

### Flow
```
Webhook Trigger → Validate Input → Load Decomposed Creative → Canonical Hash → Idempotency Check → Idea Found?
  ├─ [EXISTS] → Emit IdeaRegistered (Reuse) → Call Decision Engine → Success Response
  └─ [NEW] → Create Idea → Emit IdeaRegistered (New) → Call Decision Engine → Success Response
```

### Nodes
| ID | Name | Type |
|----|------|------|
| `webhook-trigger` | Webhook Trigger | webhook |
| `validate-input` | Validate Input | function |
| `load-decomposed` | Load Decomposed Creative | supabase |
| `canonical-hash` | Canonical Hash | function |
| `idempotency-check` | Idempotency Check | supabase |
| `idea-found-check` | Idea Found? | if |
| `create-idea` | Create Idea | supabase |
| `emit-idea-registered-new` | Emit IdeaRegistered (New) | supabase |
| `emit-idea-registered-reuse` | Emit IdeaRegistered (Reuse) | supabase |
| `call-decision-engine` | Call Decision Engine | httpRequest |
| `success-response` | Success Response | respondToWebhook |

### Events Emitted
- `IdeaRegistered` - при регистрации идеи (новой или повторной)

---

## 3. decision_engine_mvp

**ID:** `YT2d7z5h9bPy1R4v`
**Nodes:** 9
**Active:** Yes

### Purpose
Обертка для вызова Decision Engine API на Render. Загружает конфигурацию, вызывает API, эмитит результат.

### Flow
```
Webhook Trigger / Manual Trigger → Validate Input → Load Config → Extract Config Values → Call Render API → Check API Success → Emit DecisionMade → Success Response
```

### Nodes
| ID | Name | Type |
|----|------|------|
| `webhook-trigger` | Webhook Trigger | webhook |
| `manual-trigger` | Manual Trigger | manualTrigger |
| `validate-input` | Validate Input | function |
| `load-config` | Load Config | supabase |
| `extract-config` | Extract Config Values | function |
| `call-render-api` | Call Render API | httpRequest |
| `check-success` | Check API Success | if |
| `emit-decision-made` | Emit DecisionMade | supabase |
| `success-response` | Success Response | respondToWebhook |

### Events Emitted
- `DecisionMade` - после получения решения от DE

### Cold Start Protection (Issue #91)

Decision Engine на Render Free Tier уходит в sleep после 15 мин неактивности. Для защиты реализовано:

**1. Retry Logic на Call Render API node:**
```json
{
  "retryOnFail": true,
  "maxTries": 3,
  "waitBetweenTries": 15000,
  "options": { "timeout": 60000 }
}
```
- 3 попытки с интервалом 15 сек (достаточно для cold start)
- Timeout 60 сек вместо дефолтных 10 сек

**2. Keep-alive workflow (`keep_alive_decision_engine`):**
- **ID:** `ClXUPP2IvWRgu99y`
- Schedule Trigger: каждые 10 минут
- GET `https://genomai.onrender.com/health`
- Предотвращает sleep сервиса

**ВАЖНО:** Активировать keep-alive workflow в n8n UI (Schedule Trigger не активируется через API).

---

## 3a. keep_alive_decision_engine

**ID:** `ClXUPP2IvWRgu99y`
**Nodes:** 5
**Active:** Yes (требует ручной активации)

### Purpose
Keep-alive ping для предотвращения cold start Decision Engine на Render Free Tier.

### Flow
```
Schedule Trigger (*/10 * * * *) → Health Check (GET /health) → Check Response
  ├─ [OK] → Log Success (NoOp)
  └─ [FAIL] → Log Failure (alert)
```

### Nodes
| ID | Name | Type |
|----|------|------|
| `schedule-trigger` | Schedule Trigger | scheduleTrigger |
| `health-check` | Health Check | httpRequest |
| `check-response` | Check Response | if |
| `log-success` | Log Success | noOp |
| `log-failure` | Log Failure | set |

---

## 4. GenomAI - Creative Transcription

**ID:** `WMnFHqsFh8i7ddjV`
**Nodes:** 17
**Active:** Yes

### Purpose
Транскрибирует видео креативы через AssemblyAI. Скачивает из Google Drive, загружает в AssemblyAI, polling результата.

### Flow
```
Webhook → Get Creative → Check Existing Transcript → IF Transcript Exists
  ├─ [EXISTS] → Already Transcribed (NoOp)
  └─ [NEW] → Download file → Upload Audio to AssemblyAI → Start Transcription → Get Transcription Result → Switch Status
              ├─ [completed] → Insert Transcript → Emit TranscriptCreated → Update Creative Status
              ├─ [error] → Emit TranscriptionFailed → Update Creative Status Error
              └─ [queued/processing] → Wait Polling → (loop back to Get Transcription Result)
```

### Nodes
| ID | Name | Type |
|----|------|------|
| `webhook-trigger` | Webhook | webhook |
| `get-creative` | Get Creative | httpRequest |
| `check-transcript` | Check Existing Transcript | httpRequest |
| `if-exists` | IF Transcript Exists | if |
| `download-file` | Download file | googleDrive |
| `upload-audio` | Upload Audio to AssemblyAI | httpRequest |
| `wait-upload-retry` | Wait Upload Retry | wait |
| `start-transcription` | Start Transcription | httpRequest |
| `get-result` | Get Transcription Result | httpRequest |
| `switch-status` | Switch Status | switch |
| `wait-polling` | Wait Polling | wait |
| `insert-transcript` | Insert Transcript | httpRequest |
| `emit-transcript-created` | Emit TranscriptCreated | httpRequest |
| `update-status-success` | Update Creative Status | httpRequest |
| `emit-failed` | Emit TranscriptionFailed | httpRequest |
| `update-status-error` | Update Creative Status Error | httpRequest |
| `no-op-exit` | Already Transcribed | noOp |

### Events Emitted
- `TranscriptCreated` - при успешной транскрипции
- `TranscriptionFailed` - при ошибке

### Patterns
- **Polling loop**: Wait → Get Result → Switch → Wait (для async операций)
- **Retry with wait**: Upload → Wait Retry → Upload (для retry)

---

## 5. Telegram Hypothesis Delivery

**ID:** `5q3mshC9HRPpL6C0`
**Nodes:** 7
**Active:** Yes

### Purpose
Доставляет гипотезы в Telegram. Загружает гипотезы, форматирует сообщение, отправляет, персистит доставку.

### Flow
```
Webhook Trigger → Parse Webhook → Load Hypotheses → Format Message → Send Telegram Message → Persist Delivery → Emit HypothesisDelivered
```

### Nodes
| ID | Name | Type |
|----|------|------|
| `webhook-trigger-1` | Webhook Trigger | webhook |
| `parse-webhook-1` | Parse Webhook | function |
| `load-hypotheses-1` | Load Hypotheses | supabase |
| `format-message-1` | Format Message | function |
| `send-telegram-message-1` | Send Telegram Message | telegram |
| `persist-delivery-1` | Persist Delivery | supabase |
| `emit-event-1` | Emit HypothesisDelivered | supabase |

### Events Emitted
- `HypothesisDelivered` - при доставке гипотезы

---

## 6. Keitaro Poller

**ID:** `0TrVJOtHiNEEAsTN`
**Nodes:** 18
**Active:** Yes

### Purpose
Собирает метрики из Keitaro по расписанию. Итерирует по кампаниям, агрегирует метрики, сохраняет в raw_metrics.

### Flow
```
Schedule/Manual/Webhook → Load Keitaro Config → Get All Campaigns → Extract Campaign IDs → Filter Valid Campaigns → Loop Over Campaigns
  └─ Get Campaign Metrics → Check Has Data
       ├─ [HAS DATA] → Aggregate Metrics → Check Raw Metrics Exists → If Exists
       │                 ├─ [EXISTS] → Update Raw Metrics → Emit RawMetricsObserved
       │                 └─ [NEW] → Create Raw Metrics → Emit RawMetricsObserved
       └─ [NO DATA] → (back to loop)
  → Call Snapshot Creator → Call Buyer Conclusion Checker
```

### Nodes
| ID | Name | Type |
|----|------|------|
| `schedule-trigger` | Schedule Trigger | scheduleTrigger |
| `manual-trigger` | Manual Trigger | manualTrigger |
| `webhook-trigger` | Webhook Trigger | webhook |
| `load-keitaro-config` | Load Keitaro Config | supabase |
| `get-all-campaigns` | Get All Campaigns | httpRequest |
| `extract-campaign-ids` | Extract Campaign IDs | function |
| `filter-valid-campaigns` | Filter Valid Campaigns | if |
| `loop-over-campaigns` | Loop Over Campaigns | splitInBatches |
| `get-campaign-metrics` | Get Campaign Metrics | httpRequest |
| `check-has-data` | Check Has Data | if |
| `aggregate-metrics` | Aggregate Metrics | function |
| `check-exists` | Check Raw Metrics Exists | supabase |
| `if-exists` | If Exists | if |
| `update-raw-metrics` | Update Raw Metrics | supabase |
| `create-raw-metrics` | Create Raw Metrics | supabase |
| `emit-raw-metrics-observed` | Emit RawMetricsObserved | supabase |
| `call-snapshot-creator` | Call Snapshot Creator | httpRequest |
| `call-buyer-conclusion-checker` | Call Buyer Conclusion Checker | httpRequest |

### Events Emitted
- `RawMetricsObserved` - при сохранении raw метрик

### Patterns
- **Loop with splitInBatches**: для итерации по кампаниям
- **Upsert pattern**: Check Exists → If → Update/Create
- **Chain calls**: после обработки вызывает следующие workflow

---

## 7. Snapshot Creator

**ID:** `Gii8l2XwnX43Wqr4`
**Nodes:** 8
**Active:** Yes

### Purpose
Создает daily snapshots из raw_metrics. Проверяет существование, создает snapshot, вызывает Outcome Processor и Aggregator.

### Flow
```
Webhook Trigger → Check Snapshot Exists → If Not Exists
  ├─ [NEW] → Create Daily Snapshot → Emit DailyMetricsSnapshotCreated → Call Outcome Processor → Call Outcome Aggregator
  └─ [EXISTS] → Skip Existing (NoOp)
```

### Nodes
| ID | Name | Type |
|----|------|------|
| `webhook-trigger` | Webhook Trigger | webhook |
| `check-exists` | Check Snapshot Exists | supabase |
| `if-not-exists` | If Not Exists | if |
| `create-daily-snapshot` | Create Daily Snapshot | supabase |
| `emit-snapshot-created` | Emit DailyMetricsSnapshotCreated | supabase |
| `call-outcome-processor` | Call Outcome Processor | httpRequest |
| `call-outcome-aggregator` | Call Outcome Aggregator | httpRequest |
| `skip-existing` | Skip Existing | noOp |

### Events Emitted
- `DailyMetricsSnapshotCreated` - при создании snapshot

---

## 8. Outcome Aggregator

**ID:** `243QnGrUSDtXLjqU`
**Nodes:** 12
**Active:** Yes

### Purpose
Агрегирует outcomes для Learning Loop. Связывает snapshot → idea → decision, создает outcome_aggregates.

### Flow
```
Webhook Trigger → Get Snapshot Data → Get Idea Lookup → Check Idea Exists
  ├─ [NO IDEA] → No Idea - Stop (NoOp)
  └─ [EXISTS] → Get APPROVE Decision → Check Decision Exists
                 ├─ [NO DECISION] → No Decision - Stop (NoOp)
                 └─ [EXISTS] → Calculate Window ID → Insert Outcome Aggregate → Emit OutcomeAggregated → Call Learning Loop
```

### Nodes
| ID | Name | Type |
|----|------|------|
| `webhook-trigger` | Webhook Trigger | webhook |
| `get-snapshot-data` | Get Snapshot Data | supabase |
| `get-idea-lookup` | Get Idea Lookup | supabase |
| `check-idea-exists` | Check Idea Exists | if |
| `get-decision` | Get APPROVE Decision | supabase |
| `check-decision-exists` | Check Decision Exists | if |
| `calculate-window` | Calculate Window ID | set |
| `insert-outcome` | Insert Outcome Aggregate | supabase |
| `emit-outcome-aggregated` | Emit OutcomeAggregated | supabase |
| `call-learning-loop` | Call Learning Loop | httpRequest |
| `no-idea-stop` | No Idea - Stop | noOp |
| `no-decision-stop` | No Decision - Stop | noOp |

### Events Emitted
- `OutcomeAggregated` - при агрегации outcome

### Patterns
- **Guard pattern**: несколько проверок с early exit через NoOp

---

## 9. Outcome Processor

**ID:** `bbbQC4Aua5E3SYSK`
**Nodes:** 10
**Active:** Yes

### Purpose
Обрабатывает outcomes и вызывает Decision Engine для evaluation. Связывает tracker → creative → idea.

### Flow
```
Webhook Trigger → Get Creative by Tracker → Check Creative Exists
  └─ [EXISTS] → Load Decision Engine Config (parallel) + Get Idea ID (parallel) → Wait For Data → Limit To One → Prepare Request Data → Call Decision Engine → Emit HypothesisEvaluated
```

### Nodes
| ID | Name | Type |
|----|------|------|
| `webhook-trigger` | Webhook Trigger | webhook |
| `get-creative-by-tracker` | Get Creative by Tracker | supabase |
| `check-creative-exists` | Check Creative Exists | if |
| `load-config` | Load Decision Engine Config | supabase |
| `get-idea-id` | Get Idea ID | supabase |
| `wait-for-data` | Wait For Data | merge |
| `limit-to-one` | Limit To One | limit |
| `prepare-request-data` | Prepare Request Data | set |
| `call-decision-engine` | Call Decision Engine | httpRequest |
| `emit-hypothesis-evaluated` | Emit HypothesisEvaluated | supabase |

### Events Emitted
- `HypothesisEvaluated` - при evaluation гипотезы

### Patterns
- **Parallel load + merge**: загрузка данных параллельно, merge перед использованием

---

## 10. Learning Loop v2

**ID:** `fzXkoG805jQZUR3S`
**Nodes:** 5
**Active:** Yes

### Purpose
Обновляет scores идей на основе outcomes. Минимальный workflow с guard и code node.

### Flow
```
Webhook → Guard Check
  ├─ [VALID] → Process All → Respond
  └─ [INVALID] → Respond Invalid
```

### Nodes
| ID | Name | Type |
|----|------|------|
| `webhook` | Webhook | webhook |
| `guard` | Guard Check | if |
| `process` | Process All | code |
| `respond` | Respond | respondToWebhook |
| `respond_invalid` | Respond Invalid | respondToWebhook |

### Patterns
- **Code node**: вся логика в одном code node для сложных вычислений

---

## 11. Buyer Creative Registration

**ID:** `d5i9dB2GNqsbfmSD`
**Nodes:** 12
**Active:** Yes

### Purpose
Регистрация креативов от байеров через Telegram. Парсит сообщение, проверяет регистрацию байера, создает креатив.

### Flow
```
Telegram Trigger → Parse Message → Validate Input
  ├─ [INVALID] → Reply Error
  └─ [VALID] → Check Buyer Registered → Is Registered
               ├─ [NO] → Reply Not Registered
               └─ [YES] → Insert Creative → Emit CreativeRegistered → Reply Tracking Started → Call Decomposition → Reply Decomposed
```

### Nodes
| ID | Name | Type |
|----|------|------|
| `telegram-trigger` | Telegram Trigger | telegramTrigger |
| `parse-message` | Parse Message | code |
| `validate-input` | Validate Input | if |
| `check-buyer-registered` | Check Buyer Registered | supabase |
| `is-registered` | Is Registered | if |
| `insert-creative` | Insert Creative | supabase |
| `emit-event` | Emit CreativeRegistered | supabase |
| `reply-tracking` | Reply Tracking Started | telegram |
| `call-decomposition` | Call Decomposition | httpRequest |
| `reply-decomposed` | Reply Decomposed | telegram |
| `reply-error` | Reply Error | telegram |
| `reply-not-registered` | Reply Not Registered | telegram |

### Events Emitted
- `CreativeRegistered` - при регистрации креатива

### Patterns
- **Telegram bot flow**: Trigger → Parse → Validate → Process → Reply
- **Multi-step reply**: несколько reply на разных этапах

---

## 12. Buyer Test Conclusion Checker

**ID:** `4uluD04qYHhsetBy`
**Nodes:** 11
**Active:** Yes

### Purpose
Проверяет завершение тестов по spend threshold. Итерирует по tracking креативам, проверяет метрики.

### Flow
```
Webhook Trigger → Load Tracking Creatives → Loop Creatives
  └─ Get Metrics → Check Spend Threshold → Filter Concluded
       ├─ [CONCLUDED] → Update Creative Status → Emit TestConcluded → Notify Buyer → Back to Loop
       └─ [NOT CONCLUDED] → Back to Loop
  → Respond Done
```

### Nodes
| ID | Name | Type |
|----|------|------|
| `webhook-trigger` | Webhook Trigger | webhook |
| `load-tracking` | Load Tracking Creatives | supabase |
| `loop-creatives` | Loop Creatives | splitInBatches |
| `get-metrics` | Get Metrics | supabase |
| `check-threshold` | Check Spend Threshold | code |
| `filter-concluded` | Filter Concluded | if |
| `update-status` | Update Creative Status | supabase |
| `emit-concluded` | Emit TestConcluded | supabase |
| `notify-buyer` | Notify Buyer | telegram |
| `back-to-loop` | Back to Loop | noOp |
| `respond-done` | Respond Done | respondToWebhook |

### Events Emitted
- `TestConcluded` - при завершении теста

### Patterns
- **Loop with callback**: splitInBatches с возвратом через NoOp

---

## 13. Buyer Daily Digest

**ID:** `WkS1fPSxZaLmWcYy`
**Nodes:** 6
**Active:** Yes

### Purpose
Ежедневный отчет байерам с агрегированной статистикой по их креативам.

### Flow
```
Daily Schedule → Load Active Creatives → Aggregate Stats → Has Data
  ├─ [YES] → Format Digest → Send Digest
  └─ [NO] → (end)
```

### Nodes
| ID | Name | Type |
|----|------|------|
| `schedule-trigger` | Daily Schedule | scheduleTrigger |
| `load-active` | Load Active Creatives | supabase |
| `aggregate-stats` | Aggregate Stats | code |
| `check-has-data` | Has Data | if |
| `format-digest` | Format Digest | code |
| `send-digest` | Send Digest | telegram |

### Patterns
- **Scheduled job**: Schedule → Load → Process → Notify
- **Conditional send**: проверка наличия данных перед отправкой

---

## Workflow Patterns

### 1. Event Emission
Все workflow эмитят события в Supabase через insert в `events` таблицу:
```
Action → Emit Event (supabase insert) → Next Step
```

### 2. Idempotency Check
Проверка существования перед созданием:
```
Check Exists (supabase select) → If Exists
  ├─ [EXISTS] → Handle Existing
  └─ [NEW] → Create New
```

### 3. Chain Calls
Вызов следующего workflow через HTTP:
```
Process → Call Next Workflow (httpRequest) → Continue
```

### 4. Loop Pattern
Итерация по элементам:
```
splitInBatches → Process Item → Back to Loop (noOp) → splitInBatches
                             ↓
                          (done) → Respond
```

### 5. Parallel Load + Merge
Загрузка данных параллельно:
```
├─ Load A → Merge
└─ Load B → Merge → Continue
```

### 6. Guard Pattern
Early exit при невалидных данных:
```
Check → If Valid
  ├─ [VALID] → Process
  └─ [INVALID] → NoOp / Error Response
```

---

## Node Naming Conventions

| Pattern | Example |
|---------|---------|
| Trigger | `Webhook Trigger`, `Schedule Trigger`, `Telegram Trigger` |
| Load/Get | `Load Keitaro Config`, `Get Creative`, `Get Metrics` |
| Check/Validate | `Check Exists`, `Validate Input`, `Check Threshold` |
| Condition | `If Exists`, `Is Registered`, `Has Data` |
| Create/Insert | `Create Creative`, `Insert Transcript` |
| Update | `Update Raw Metrics`, `Update Creative Status` |
| Emit | `Emit EventName` (всегда с названием события) |
| Call | `Call Decision Engine`, `Call Next Workflow` |
| Response | `Success Response`, `Error Response`, `Respond` |
| Loop control | `Loop Over Items`, `Back to Loop` |
| Stop | `No Idea - Stop`, `Skip Existing` |

---

## Supabase Node Configuration

Стандартные headers для schema `genomai`:
```json
{
  "Accept-Profile": "genomai",
  "Content-Profile": "genomai"
}
```

---

## Telegram Node Configuration

**ОБЯЗАТЕЛЬНО** для всех Telegram нод (telegram, telegramTrigger):

```json
{
  "additionalFields": {
    "appendAttribution": false
  }
}
```

Это отключает автоматическую подпись "This message was sent automatically with n8n" в сообщениях.

### Применяется к нодам:
- `n8n-nodes-base.telegram` - отправка сообщений
- Все ноды с типом `telegram` в workflows

### Пример конфигурации:
```json
{
  "parameters": {
    "chatId": "={{ $json.chat_id }}",
    "text": "Сообщение",
    "additionalFields": {
      "appendAttribution": false
    }
  },
  "type": "n8n-nodes-base.telegram",
  "typeVersion": 1.2
}
```

---

## HTTP Request Patterns

### Internal Workflow Call
```
URL: https://<n8n-host>/webhook/<path>
Method: POST
Body: { "data": "..." }
```

### Decision Engine API
```
URL: https://genomai.onrender.com/api/decision/
Method: POST
Headers: { "Authorization": "Bearer <API_KEY>" }
```

### Learning Loop API
```
URL: https://genomai.onrender.com/learning/process
Method: POST
Headers: { "Authorization": "Bearer <API_KEY>" }
```

### Keitaro API
```
URL: https://<keitaro-host>/admin_api/v1/...
Method: GET/POST
Headers: { "Api-Key": "..." }
```

---

## 14. hypothesis_factory_generate

**ID:** `oxG1DqxtkTGCqLZi`
**Nodes:** 14
**Active:** Yes

### Purpose
Генерирует гипотезы для approved ideas через LLM. Форматирует prompt, вызывает OpenAI, сохраняет результат.

### Flow
```
Webhook Trigger → Load Idea + Decision → Format Prompt → Call OpenAI → Parse Response → Save Hypothesis → Emit HypothesisGenerated → Call Delivery
```

### Events Emitted
- `HypothesisGenerated` - при генерации гипотезы

---

## 15. Buyer Onboarding

**ID:** `hgTozRQFwh4GLM0z`
**Nodes:** 18
**Active:** Yes

### Purpose
Онбординг новых байеров через Telegram с автоматической загрузкой исторических креативов. Multi-step flow с сохранением состояния.

### Flow
```
Telegram Trigger → Get Buyer State → Check Existing Buyer → Route by State
  ├─ [0: /start] → Create State: Awaiting Name → Reply: Ask Name
  ├─ [1: awaiting_name] → Update State: Awaiting Geo → Reply: Ask Geo
  ├─ [2: awaiting_geo] → Update State: Awaiting Vertical → Reply: Ask Vertical
  ├─ [3: awaiting_vertical] → Update State: Awaiting Keitaro → Reply: Ask Keitaro Source
  ├─ [4: awaiting_keitaro_source] → Get Context → Insert Buyer (with keitaro_source)
  │                                 → Delete State → Call Historical Loader → Reply: Loading History
  └─ [5: already registered] → Reply: Already Registered
```

### Nodes
| ID | Name | Type |
|----|------|------|
| `telegram-trigger` | Telegram Trigger | telegramTrigger |
| `get-state` | Get Buyer State | supabase |
| `check-existing-buyer` | Check Existing Buyer | supabase |
| `route-state` | Route by State | switch |
| `create-state-name` | Create State: Awaiting Name | supabase |
| `reply-ask-name` | Reply: Ask Name | telegram |
| `update-state-geo` | Update State: Awaiting Geo | supabase |
| `reply-ask-geo` | Reply: Ask Geo | telegram |
| `update-state-vertical` | Update State: Awaiting Vertical | supabase |
| `reply-ask-vertical` | Reply: Ask Vertical | telegram |
| `update-state-keitaro` | Update State: Awaiting Keitaro | supabase |
| `reply-ask-keitaro` | Reply: Ask Keitaro Source | telegram |
| `get-context-keitaro` | Get Context with Keitaro | code |
| `insert-buyer-new` | Insert Buyer with Keitaro | supabase |
| `delete-state-new` | Delete State New | supabase |
| `call-historical-loader` | Call Historical Loader | httpRequest |
| `reply-loading-history` | Reply: Loading History | telegram |
| `reply-already-registered` | Reply: Already Registered | telegram |

### Events Emitted
- `BuyerRegistered` - при завершении регистрации (implicit via insert)

### Patterns
- **Multi-step state machine**: Route by State switch с 6 outputs
- **Chain workflow call**: После регистрации вызывает Historical Loader

---

## 15a. Buyer Historical Loader

**ID:** `lmiWkYTRZPSpydJH`
**Nodes:** 16
**Active:** Yes

### Purpose
Загружает все campaigns из Keitaro для нового buyer'а, фильтрует, создаёт очередь импорта и отправляет первый батч в Telegram.

### Flow
```
Webhook Trigger → Set Input → Load Keitaro Config → Get All Campaigns → Filter Campaigns
  → Has Campaigns?
    ├─ [YES] → Get Metrics for Campaigns → Process Metrics → Has Valid Campaigns?
    │           ├─ [YES] → Create Queue Entries → Insert Queue → Prepare First Batch
    │           │          → Update Buyer State → Send Batch Message
    │           └─ [NO] → No Valid Campaigns (telegram)
    └─ [NO] → No Campaigns Message (telegram)
```

### Input (from Buyer Onboarding)
```json
{
  "buyer_id": "uuid",
  "keitaro_source": "danny",
  "chat_id": 123456789,
  "buyer_name": "Danny",
  "telegram_id": "123456789"
}
```

### Filter Criteria
- Source: `campaign.parameters.source.name` == `keitaro_source`
- Exclude: campaigns where `name` contains "coin"
- Date: created within last 30 days
- Activity: `clicks > 0` OR `created_at = today`

### Nodes
| ID | Name | Type |
|----|------|------|
| `webhook-trigger` | Webhook Trigger | webhook |
| `set-input` | Set Input | set |
| `load-keitaro-config` | Load Keitaro Config | supabase |
| `get-campaigns` | Get All Campaigns | httpRequest |
| `filter-campaigns` | Filter Campaigns | code |
| `check-campaigns` | Has Campaigns? | if |
| `get-metrics-batch` | Get Metrics for Campaigns | httpRequest |
| `process-metrics` | Process Metrics | code |
| `check-valid-campaigns` | Has Valid Campaigns? | if |
| `create-queue-entries` | Create Queue Entries | code |
| `insert-queue` | Insert Queue | httpRequest |
| `prepare-batch` | Prepare First Batch | code |
| `update-state` | Update Buyer State | supabase |
| `send-batch-message` | Send Batch Message | telegram |
| `no-campaigns-msg` | No Campaigns Message | telegram |
| `no-valid-campaigns` | No Valid Campaigns | telegram |

### Telegram Message Format
```
📦 Загрузка исторических данных

Отправь ссылки на видео для следующих кампаний:

📹 #123 | clicks: 500 | conv: 10 | CPA: $5.00
📹 #456 | clicks: 300 | conv: 5 | CPA: $8.00
...

━━━━━━━━━━━━━━━━━━━━
Ответь ссылками в том же порядке (по одной на строку)
```

---

## 15b. Buyer Historical URL Handler

**ID:** `A8gKvO5810L1lusZ`
**Nodes:** 18
**Active:** Yes

### Purpose
Обрабатывает ответы buyer'а с video URLs, обновляет очередь, запускает импорт, отправляет следующий батч.

### Flow
```
Telegram Trigger → Get Buyer State → Awaiting URLs?
  ├─ [YES] → Parse URLs → Has Matches?
  │           ├─ [YES] → Split Matches → Loop:
  │           │          → Update Queue Entry → Call Historical Import → Aggregate Results
  │           │          → Check Remaining → Route Action
  │           │             ├─ [next_batch] → Load Next Batch → Prepare Next Batch
  │           │             │                → Update State Next → Send Next Batch
  │           │             └─ [complete] → Delete State → Send Complete
  │           └─ [NO] → No Matches Reply
  └─ [NO] → (stop - not awaiting URLs)
```

### Input Format
Buyer отправляет URLs по одному на строку:
```
https://drive.google.com/file/d/xxx/view
https://drive.google.com/file/d/yyy/view
https://drive.google.com/file/d/zzz/view
```

### Nodes
| ID | Name | Type |
|----|------|------|
| `telegram-trigger` | Telegram Trigger | telegramTrigger |
| `get-buyer-state` | Get Buyer State | supabase |
| `check-state` | Awaiting URLs? | if |
| `parse-urls` | Parse URLs | code |
| `check-matches` | Has Matches? | if |
| `split-matches` | Split Matches | splitOut |
| `update-queue` | Update Queue Entry | httpRequest |
| `call-import` | Call Historical Import | httpRequest |
| `aggregate-results` | Aggregate Results | aggregate |
| `check-remaining` | Check Remaining | code |
| `route-action` | Route Action | switch |
| `load-next-batch` | Load Next Batch | supabase |
| `prepare-next-batch` | Prepare Next Batch | code |
| `update-state-next` | Update State Next | supabase |
| `send-next-batch` | Send Next Batch | telegram |
| `delete-state` | Delete State | supabase |
| `send-complete` | Send Complete | telegram |
| `no-matches-reply` | No Matches Reply | telegram |

### Completion Message
```
✅ Все исторические креативы обработаны!

🎓 Система обучилась на твоих данных.

Теперь можешь регистрировать новые креативы:
video_url tracker_id

/stats - твоя статистика
```

---

## 16. Buyer Stats Command

**ID:** `rHuT8dYyIXoiHMAV`
**Nodes:** 9
**Active:** Yes

### Purpose
Команда /stats для байеров - показывает статистику по их креативам.

### Flow
```
Telegram Trigger → Parse /stats → Load Buyer Creatives → Aggregate Stats → Format Message → Send Stats
```

### Patterns
- **Command handler**: Telegram Trigger → Parse → Process → Reply

---

## 16a. Telegram Router

**ID:** `BuyQncnHNb7ulL6z`
**Nodes:** 13
**Active:** Yes

### Purpose
Центральный маршрутизатор для всех Telegram сообщений. Определяет тип сообщения и перенаправляет в соответствующий workflow.

### Flow
```
Telegram Trigger → Determine Message Type → Route by Type
  ├─ [/start] → Call Buyer Onboarding
  ├─ [/stats] → Call Buyer Stats Command
  ├─ [video] → Call Buyer Creative Registration
  ├─ [text with URLs] → Check Buyer State → Route
  │    ├─ [awaiting_urls] → Call Historical URL Handler
  │    └─ [other] → Call Creative Registration
  └─ [unknown] → Reply Help Message
```

### Nodes
| ID | Name | Type |
|----|------|------|
| `telegram-trigger` | Telegram Trigger | telegramTrigger |
| `determine-type` | Determine Message Type | code |
| `route-type` | Route by Type | switch |
| `call-onboarding` | Call Buyer Onboarding | httpRequest |
| `call-stats` | Call Buyer Stats | httpRequest |
| `call-registration` | Call Creative Registration | httpRequest |
| `check-buyer-state` | Check Buyer State | supabase |
| `route-state` | Route by State | if |
| `call-url-handler` | Call Historical URL Handler | httpRequest |
| `reply-help` | Reply Help Message | telegram |

### Patterns
- **Central router**: единая точка входа для всех Telegram сообщений
- **Type detection + routing**: определение типа и перенаправление
- **State-aware routing**: маршрутизация с учётом состояния buyer

---

## 17. Historical Creative Import

**ID:** `1FC7amTd3dCRZPEa`
**Nodes:** 17
**Active:** No (manual trigger)

### Purpose
Импорт исторических креативов с метриками из Keitaro для создания первоначального обучающего стека.

### Flow
```
Manual Trigger → Set Input Data → Load Keitaro Config → Get Historical Metrics → Aggregate Metrics → Has Metrics?
  ├─ [YES] → Create Creative → Emit CreativeRegistered → Call Transcription → Wait 120s
  │          → Check Idea Created → Idea Ready?
  │             └─ [YES] → Create Outcome Aggregate → Emit OutcomeImported → Call Learning Loop → Success Summary
  └─ [NO] → No Metrics Response
```

### Input Data
При запуске через Manual Trigger необходимо передать:
```json
{
  "campaign_id": "123",
  "video_url": "https://drive.google.com/file/d/xxx/view",
  "buyer_id": "uuid-of-buyer",
  "date_from": "2024-01-01",
  "date_to": "2024-12-25"
}
```

### Nodes
| ID | Name | Type |
|----|------|------|
| `manual-trigger` | Manual Trigger | manualTrigger |
| `set-input-data` | Set Input Data | set |
| `load-keitaro-config` | Load Keitaro Config | supabase |
| `get-historical-metrics` | Get Historical Metrics | httpRequest |
| `aggregate-historical` | Aggregate Historical Metrics | code |
| `check-has-metrics` | Has Metrics? | if |
| `create-creative` | Create Creative | supabase |
| `emit-creative-registered` | Emit CreativeRegistered | supabase |
| `call-transcription` | Call Transcription | httpRequest |
| `wait-for-processing` | Wait for Processing | wait |
| `check-idea-created` | Check Idea Created | supabase |
| `idea-ready-check` | Idea Ready? | if |
| `create-outcome` | Create Outcome Aggregate | supabase |
| `emit-outcome-imported` | Emit OutcomeImported | supabase |
| `call-learning-loop` | Call Learning Loop | httpRequest |
| `success-summary` | Success Summary | set |
| `no-metrics-response` | No Metrics Response | set |

### Events Emitted
- `CreativeRegistered` - при создании креатива
- `OutcomeImported` - при импорте исторических метрик

### Patterns
- **Historical import**: Manual Trigger с input data
- **Chain workflow calls**: Transcription → Decomposition → Idea Registry
- **Outcome with origin_type**: `historical` для отличия от realtime данных

---

## 18. Historical Import Batch Loader

**ID:** `RLO7XEoDV3lj74cl`
**Nodes:** 15
**Active:** No (manual trigger)

### Purpose
Загружает все campaigns из Keitaro, извлекает buyer source, создаёт записи в очереди импорта и отправляет запросы video_url в Telegram.

### Flow
```
Manual Trigger → Load Keitaro Config → Get All Campaigns → Filter Active (extract keitaro_source) → Loop Campaigns
  └─ Check Queue → Not In Queue?
       ├─ [NEW] → Get Metrics → Aggregate → Lookup Buyer (by keitaro_source) → Process Buyer
       │          → Create Queue Entry (with buyer_id) → Send Telegram Request → Loop
       └─ [EXISTS] → Skip → Loop
```

### Buyer Extraction
- Извлекает `keitaro_source` из `campaign.parameters.source.name`
- Lookup buyer по полю `buyers.keitaro_source`
- Если buyer не найден - сообщение в Telegram указывает на это

### Events
- Отправляет сообщение в Telegram с запросом video_url для каждой новой campaign
- Показывает статус buyer'а (найден / не найден)

---

## 19. Historical Import Video Handler

**ID:** `UYgvqpsU3TMzb2Qd`
**Nodes:** 10
**Active:** Yes (Telegram trigger)

### Purpose
Обрабатывает ответы из Telegram с video_url и запускает импорт.

### Flow
```
Telegram Trigger → Parse Message → Valid Format?
  ├─ [YES] → Check Queue Exists → Queue Found?
  │           ├─ [YES] → Update Queue → Call Import Workflow → Reply Success
  │           └─ [NO] → Reply Not Found
  └─ [NO] → Reply Invalid Format
```

### Input Format
```
campaign_id video_url
```
Пример: `123 https://drive.google.com/file/d/xxx/view`

---

## Historical Import Flow

### Новый процесс (интегрирован в Onboarding)

```
1. Buyer отправляет /start в Telegram
   ↓
2. Buyer Onboarding собирает данные:
   - Имя → Гео → Вертикаль → Keitaro Source
   ↓
3. После регистрации buyer'а вызывается "Buyer Historical Loader":
   - Загружает campaigns из Keitaro по source
   - Фильтрует: исключает "coin", 30 дней, clicks > 0 OR сегодня
   - Создаёт записи в historical_import_queue
   - Отправляет первый батч (5 campaigns) в Telegram
   ↓
4. Buyer отправляет URLs (по одному на строку):
   https://drive.google.com/file/d/xxx/view
   https://drive.google.com/file/d/yyy/view
   ↓
5. "Buyer Historical URL Handler" получает ответ:
   - Парсит URLs, матчит с campaigns по порядку
   - Обновляет queue (video_url, status: ready)
   - Вызывает "Historical Creative Import" для каждого
   - Отправляет следующий батч или завершает
   ↓
6. "Historical Creative Import" обрабатывает каждый креатив:
   - Create Creative → Transcription → Decomposition → Idea
   - Create Outcome Aggregate (origin: historical)
   - Call Learning Loop
```

### Legacy процесс (ручной)

```
1. Запустить "Historical Import Batch Loader" (manual)
   ↓
2. Workflow загружает campaigns из Keitaro
   ↓
3. Для каждой campaign без video_url:
   - Создаёт запись в historical_import_queue (status: pending_video)
   - Отправляет запрос в Telegram
   ↓
4. Пользователь отвечает в Telegram: "123 https://drive.google.com/..."
   ↓
5. "Historical Import Video Handler" получает ответ:
   - Обновляет queue (status: ready, video_url: ...)
   - Вызывает "Historical Creative Import"
   ↓
6. "Historical Creative Import" обрабатывает:
   - Create Creative → Transcription → Decomposition → Idea
   - Create Outcome Aggregate (origin: historical)
   - Call Learning Loop
```

### Таблица очереди

`genomai.historical_import_queue`:
| Поле | Тип | Описание |
|------|-----|----------|
| campaign_id | TEXT | ID кампании в Keitaro |
| video_url | TEXT | URL видео (nullable) |
| buyer_id | UUID | ID байера (nullable, FK → buyers) |
| keitaro_source | TEXT | Имя buyer'а из Keitaro (campaign.parameters.source.name) |
| status | TEXT | pending_video / ready / processing / completed / failed |
| metrics | JSONB | Метрики из Keitaro |
| date_from | DATE | Начало периода |
| date_to | DATE | Конец периода |

### Buyer Mapping

Система автоматически извлекает buyer из Keitaro campaign:
- `campaign.parameters.source.name` содержит имя байера (keitaro_source)
- Buyer lookup происходит по полю `buyers.keitaro_source`
- Если buyer не найден - создаётся уведомление в Telegram

**Таблица buyers**:
| Поле | Тип | Описание |
|------|-----|----------|
| id | UUID | Primary key |
| telegram_id | TEXT | Telegram ID для уведомлений |
| keitaro_source | TEXT | Идентификатор в Keitaro (UNIQUE) |
| name | TEXT | Имя байера |
| ... | ... | ...

---

## Common Issues & Anti-patterns

### 1. Check→If Anti-pattern (КРИТИЧНО)

**Проблема:** Supabase `getAll` → If node → Create/Update. Когда getAll возвращает пустой массив, downstream nodes не получают данные и workflow молча останавливается.

**Как найти:**
```
Supabase(getAll) → If($json.id ? true : false) → Create/Update
```

**Решение:**
- Обойти If node, использовать Supabase create напрямую
- Добавить `onError: continueRegularOutput` на create node
- Или добавить прямое соединение от триггера к create node (bypass)

**Примеры исправленных workflows:**
- Keitaro Poller: заменён Check→If→Update/Create на прямой Upsert
- Snapshot Creator: добавлен bypass connection

---

### 2. SplitInBatches Wrong Output

**Проблема:** SplitInBatches имеет 2 выхода:
- **Output 0** = "done" (когда ВСЕ items обработаны)
- **Output 1** = "loop" (для обработки КАЖДОГО item)

**Ошибка:** Processing node подключен к output 0 вместо output 1

**Как найти:**
```json
"connections": {
  "Loop Over Items": {
    "main": [
      [{ "node": "Done Handler" }],    // output 0 - done
      [{ "node": "Process Item" }]     // output 1 - loop ← сюда!
    ]
  }
}
```

**Решение:** Подключить processing node к output 1

---

### 3. Wrong Webhook URL/Path

**Проблема:** HTTP Request вызывает webhook другого workflow с неправильным URL

**Частые ошибки:**
- Wrong host: `unighaz.app.n8n.cloud` vs `kazamaqwe.app.n8n.cloud`
- Wrong path: `learning-loop` vs `learning-loop-v2`
- Missing `/webhook/` prefix

**Как найти:**
```javascript
// Проверь все HTTP Request nodes
node.parameters.url.includes('webhook')
```

**Решение:**
- Проверить webhook path в целевом workflow (параметр `path`)
- Использовать правильный host: `kazamaqwe.app.n8n.cloud`

---

### 4. $env Blocked in n8n Cloud

**Проблема:** `$env.VARIABLE` не работает в n8n Cloud (заблокировано по безопасности)

**Как найти:**
```javascript
expression.includes('$env.')
```

**Решение:**
- Загружать конфиг из Supabase `genomai.config` таблицы
- Использовать Supabase credentials (node credentials)
- Hardcode значения (не рекомендуется)

---

### 5. Partial Update Resets Parameters

**Проблема:** При `n8n_update_partial_workflow` обновление одного параметра может сбросить другие

**Пример:**
```javascript
// Обновляем только URL
{ "parameters": { "url": "new-url" } }
// Результат: method сбрасывается на GET, sendBody на false
```

**Решение:**
- Всегда включать все связанные параметры в partial update:
```javascript
{
  "parameters": {
    "method": "POST",
    "url": "new-url",
    "sendBody": true,
    "jsonBody": "..."
  }
}
```

---

### 6. Supabase Node: No Upsert

**Проблема:** Supabase node не поддерживает upsert (ON CONFLICT)

**Доступные операции:** create, update, delete, getAll

**Решение для upsert pattern:**
1. Использовать `create` с `onError: continueRegularOutput`
2. Или Code node с HTTP Request к Supabase REST API:
```javascript
// В Code node
await this.helpers.httpRequest({
  method: 'POST',
  url: `${baseUrl}/table?on_conflict=id`,
  headers: { 'Prefer': 'resolution=merge-duplicates' },
  body: data
});
```

---

### Review Skill

Для автоматической проверки workflows используй:
```
/n8n-review <workflow-id>
```

Проверяет все вышеуказанные проблемы автоматически |
