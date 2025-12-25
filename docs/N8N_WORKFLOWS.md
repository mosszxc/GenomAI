# n8n Workflows Reference

## Overview

GenomAI использует 17 активных workflow для оркестрации пайплайна. Все workflow следуют event-driven архитектуре с emit событий в Supabase.

## Workflow Index

| ID | Name | Trigger | Purpose | Active |
|----|------|---------|---------|--------|
| `dvZvUUmhtPzYOK7X` | creative_ingestion_webhook | Webhook | Регистрация креативов | ❌ |
| `cGSyJPROrkqLVHZP` | idea_registry_create | Webhook | Создание идей из креативов | ✅ |
| `YT2d7z5h9bPy1R4v` | decision_engine_mvp | Webhook/Manual | Вызов Decision Engine API | ✅ |
| `WMnFHqsFh8i7ddjV` | GenomAI - Creative Transcription | Webhook | Транскрипция видео через AssemblyAI | ✅ |
| `mv6diVtqnuwr7qev` | creative_decomposition_llm | Webhook | LLM декомпозиция креативов | ✅ |
| `oxG1DqxtkTGCqLZi` | hypothesis_factory_generate | Webhook | Генерация гипотез через LLM | ✅ |
| `5q3mshC9HRPpL6C0` | Telegram Hypothesis Delivery | Webhook | Доставка гипотез в Telegram | ✅ |
| `0TrVJOtHiNEEAsTN` | Keitaro Poller | Schedule/Webhook | Сбор метрик из Keitaro | ✅ |
| `Gii8l2XwnX43Wqr4` | Snapshot Creator | Webhook | Создание daily snapshots | ✅ |
| `243QnGrUSDtXLjqU` | Outcome Aggregator | Webhook | Агрегация outcomes для Learning Loop | ✅ |
| `bbbQC4Aua5E3SYSK` | Outcome Processor | Webhook | Обработка outcomes, вызов DE | ✅ |
| `fzXkoG805jQZUR3S` | Learning Loop v2 | Webhook | Обновление scores идей | ✅ |
| `d5i9dB2GNqsbfmSD` | Buyer Creative Registration | Telegram | Регистрация креативов от байеров | ✅ |
| `4uluD04qYHhsetBy` | Buyer Test Conclusion Checker | Webhook | Проверка завершения тестов | ✅ |
| `WkS1fPSxZaLmWcYy` | Buyer Daily Digest | Schedule | Ежедневный отчет байерам | ✅ |
| `hgTozRQFwh4GLM0z` | Buyer Onboarding | Telegram | Онбординг новых байеров | ✅ |
| `rHuT8dYyIXoiHMAV` | Buyer Stats Command | Telegram | Команда /stats для байеров | ✅ |

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
**Nodes:** 15
**Active:** Yes

### Purpose
Онбординг новых байеров через Telegram. Multi-step flow с сохранением состояния.

### Flow
```
Telegram Trigger → Check Command → Is /start?
  ├─ [YES] → Check Existing Buyer → Is New?
  │           ├─ [NEW] → Set State awaiting_name → Reply Ask Name
  │           └─ [EXISTS] → Reply Already Registered
  └─ [NO] → Load State → Process Step (name/geo/vertical) → Save Buyer → Reply Welcome
```

### Events Emitted
- `BuyerRegistered` - при завершении регистрации

---

## 16. Buyer Stats Command

**ID:** `rHuT8dYyIXoiHMAV`
**Nodes:** 8
**Active:** Yes

### Purpose
Команда /stats для байеров - показывает статистику по их креативам.

### Flow
```
Telegram Trigger → Parse /stats → Load Buyer Creatives → Aggregate Stats → Format Message → Send Stats
```

### Patterns
- **Command handler**: Telegram Trigger → Parse → Process → Reply
