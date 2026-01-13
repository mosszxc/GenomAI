# GenomAI System Capabilities v2.0

Полный список функциональных возможностей системы.

**Последнее обновление**: 2026-01-12

---

## 1. VIDEO INGESTION

### 1.1 Приём видео
| ID | Capability | Проверка | Статус |
|----|------------|----------|--------|
| ING-01 | Buyer отправляет видео в Telegram | Видео сохраняется в `creatives` | ✅ |
| ING-02 | Buyer отправляет ссылку на видео | URL парсится, видео скачивается | ✅ |
| ING-03 | Google Drive / Dropbox auto-convert | Ссылки конвертируются в direct URL | ✅ |
| ING-04 | Создание записи creative с buyer_id | `creatives.buyer_id` заполнен | ✅ |
| ING-05 | Дедупликация по video_url | Повторная ссылка не создаёт дубликат | ✅ |

### 1.2 Транскрипция
| ID | Capability | Проверка | Статус |
|----|------------|----------|--------|
| ING-10 | Транскрипция через AssemblyAI | `transcripts` запись создана | ✅ |
| ING-11 | Transcript persistence | Сохранение перед decomposition | ✅ |
| ING-12 | Stuck transcription monitoring | MaintenanceWorkflow детектит | ✅ |

### 1.3 Temporal Workflows
- `CreativePipelineWorkflow` (creative-pipeline queue)
- `CreativeRegistrationWorkflow` (telegram queue)
- `HistoricalVideoHandlerWorkflow` (telegram queue)

---

## 2. DECOMPOSITION

### 2.1 LLM-разбор
| ID | Capability | Проверка | Статус |
|----|------------|----------|--------|
| DEC-01 | LLM извлекает canonical fields | Все required fields в payload | ✅ |
| DEC-02 | Валидация output против JSON Schema | valid:true | ✅ |
| DEC-03 | Создание decomposed_creative | Запись в `decomposed_creatives` | ✅ |
| DEC-04 | Module extraction | Модули в `module_bank` | ✅ |

### 2.2 Modular Creative System
| ID | Capability | Проверка | Статус |
|----|------------|----------|--------|
| MOD-01 | Module extraction из креативов | Записи в `module_bank` | ✅ |
| MOD-02 | Module learning на outcomes | `module_learnings` обновляется | ✅ |
| MOD-03 | Module reuse в hypothesis | Модули переиспользуются | ✅ |

---

## 3. IDEA REGISTRY

### 3.1 Создание идей
| ID | Capability | Проверка | Статус |
|----|------------|----------|--------|
| IDR-01 | Создание idea из decomposed_creative | Запись в `ideas` | ✅ |
| IDR-02 | Генерация canonical_hash | Уникальный hash | ✅ |
| IDR-03 | Идемпотентность по hash | Нет дубликатов | ✅ |
| IDR-04 | Avatar association | avatar_id заполнен | ✅ |

---

## 4. DECISION ENGINE

### 4.1 Decision Flow
| ID | Capability | Проверка | Статус |
|----|------------|----------|--------|
| DE-01 | POST /api/decision/ | Возвращает decision + trace | ✅ |
| DE-02 | 4 checks последовательно | trace.checks содержит 4 записи | ✅ |
| DE-03 | Первый failed останавливает | Остальные не выполняются | ✅ |
| DE-04 | Idempotency guard | Повторный запрос не дублирует | ✅ |

### 4.2 Checks
| Check | Действие | Result |
|-------|----------|--------|
| schema_validity | Проверка полей | REJECT |
| death_memory | Проверка death_state | REJECT |
| fatigue_constraint | Проверка выгорания | REJECT |
| risk_budget | Проверка лимитов | DEFER |

---

## 5. HYPOTHESIS FACTORY

### 5.1 Генерация гипотез
| ID | Capability | Проверка | Статус |
|----|------------|----------|--------|
| HF-01 | Создание hypothesis из approved idea | Запись в `hypotheses` | ✅ |
| HF-02 | Modular hypothesis generation | Из module_bank | ✅ |
| HF-03 | Premise selection | Из premise_bank | ✅ |
| HF-04 | Retry mechanism | Повтор при failed delivery | ✅ |

### 5.2 Temporal Workflows
- `ModularHypothesisWorkflow` (creative-pipeline queue)

---

## 6. KNOWLEDGE EXTRACTION

### 6.1 Premise Layer
| ID | Capability | Проверка | Статус |
|----|------------|----------|--------|
| KNW-01 | Premise extraction из transcripts | `premise_bank` записи | ✅ |
| KNW-02 | Premise learning на outcomes | Win rate обновляется | ✅ |
| KNW-03 | Premise selection для hypothesis | Лучшие premises выбираются | ✅ |

### 6.2 Inspiration System
| ID | Capability | Проверка | Статус |
|----|------------|----------|--------|
| KNW-10 | Inspiration detection | Предотвращение деградации | ✅ |
| KNW-11 | Knowledge application | Применение к новым креативам | ✅ |

### 6.3 Temporal Workflows
- `KnowledgeIngestionWorkflow` (knowledge queue)
- `PremiseExtractionWorkflow` (knowledge queue)
- `KnowledgeApplicationWorkflow` (knowledge queue)

---

## 7. METRICS & LEARNING

### 7.1 Keitaro Polling
| ID | Capability | Проверка | Статус |
|----|------------|----------|--------|
| MET-01 | Polling каждые 10 минут | Данные в `raw_metrics_current` | ✅ |
| MET-02 | profit_confirmed metric | Подтверждённая прибыль | ✅ |
| MET-03 | Daily snapshots | `daily_metrics_snapshot` | ✅ |

### 7.2 Learning Loop
| ID | Capability | Проверка | Статус |
|----|------------|----------|--------|
| LRN-01 | Hourly learning cycle | Каждый час | ✅ |
| LRN-02 | Confidence updates | `idea_confidence_versions` | ✅ |
| LRN-03 | Component learning | `component_learnings` | ✅ |
| LRN-04 | Module learning | `module_learnings` | ✅ |
| LRN-05 | Fatigue versioning | История fatigue | ✅ |
| LRN-06 | Death detection | 3→soft_dead, 5→hard_dead | ✅ |
| LRN-07 | Trend calculation | Volatility, trend | ✅ |

### 7.3 Temporal Workflows
- `KeitaroPollerWorkflow` (metrics queue, 10 min)
- `MetricsProcessingWorkflow` (metrics queue, 30 min)
- `LearningLoopWorkflow` (metrics queue, 1 hour)

---

## 8. RECOMMENDATIONS

### 8.1 Генерация
| ID | Capability | Проверка | Статус |
|----|------------|----------|--------|
| REC-01 | Daily recommendations | 09:00 UTC | ✅ |
| REC-02 | 75% exploitation | Проверенные компоненты | ✅ |
| REC-03 | 25% exploration | Thompson Sampling | ✅ |
| REC-04 | Фильтрация по buyer/geo/vertical | Релевантность | ✅ |

### 8.2 Temporal Workflows
- `DailyRecommendationWorkflow` (metrics queue, 09:00 UTC)
- `SingleRecommendationDeliveryWorkflow` (metrics queue)

---

## 9. TELEGRAM BOT

### 9.1 Buyer Commands
| Command | Description | Статус |
|---------|-------------|--------|
| `/start` | Онбординг | ✅ |
| `/help` | Справка | ✅ |
| `/stats` | Статистика buyer | ✅ |
| `/feedback` | Bug report → GitHub | ✅ |

### 9.2 Analytics Commands
| Command | Description | Статус |
|---------|-------------|--------|
| `/genome` | Component heatmap | ✅ |
| `/trends` | Win rate charts | ✅ |
| `/confidence` | Confidence intervals | ✅ |
| `/drift` | Performance drift | ✅ |
| `/correlations` | Component synergy | ✅ |
| `/recommend` | Auto-recommendations | ✅ |

### 9.3 Agent Commands
| Command | Description | Статус |
|---------|-------------|--------|
| `/ag1`-`/ag5` | Agent identity | ✅ |
| `/next` | Next task | ✅ |

### 9.4 Admin Commands
| Command | Description | Статус |
|---------|-------------|--------|
| `/health` | System health | ✅ |
| `/schedules` | Temporal schedules | ✅ |

### 9.5 Temporal Workflows
- `BuyerOnboardingWorkflow` (telegram queue)
- `HistoricalImportWorkflow` (telegram queue)

---

## 10. MULTI-AGENT ORCHESTRATION

### 10.1 Task Queue
| ID | Capability | Проверка | Статус |
|----|------------|----------|--------|
| AGT-01 | Task queue в Supabase | `agent_tasks` таблица | ✅ |
| AGT-02 | Agent identity | /ag1-/ag5 команды | ✅ |
| AGT-03 | Orphan detection | Незавершённые задачи | ✅ |
| AGT-04 | Task assignment | Автораспределение | ✅ |

---

## 11. MAINTENANCE

### 11.1 Health & Cleanup
| ID | Capability | Проверка | Статус |
|----|------------|----------|--------|
| MNT-01 | Health check workflow | Каждые 6 часов | ✅ |
| MNT-02 | Stuck creatives archive | Архивация зависших | ✅ |
| MNT-03 | Integrity check | Проверка связей | ✅ |
| MNT-04 | Orphaned records cleanup | Чистка сирот | ✅ |
| MNT-05 | Recovery workflow conflicts | Предотвращение | ✅ |

### 11.2 Temporal Workflows
- `MaintenanceWorkflow` (metrics queue, 6 hours)
- `HealthCheckWorkflow` (metrics queue)

---

## 12. API ENDPOINTS

### 12.1 Core API
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/decision/` | POST | Submit decision |
| `/learning/process` | POST | Trigger learning |
| `/learning/status` | GET | Learning status |

### 12.2 Schedule API
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/schedules/` | GET | List schedules |
| `/api/schedules/{id}` | GET | Get schedule |
| `/api/schedules/{id}/trigger` | POST | Trigger schedule |
| `/api/schedules/{id}/pause` | POST | Pause schedule |
| `/api/schedules/{id}/resume` | POST | Resume schedule |

---

## 13. TEMPORAL SCHEDULES

| Schedule ID | Workflow | Interval |
|-------------|----------|----------|
| keitaro-poller | KeitaroPollerWorkflow | 10 min |
| metrics-processor | MetricsProcessingWorkflow | 30 min |
| learning-loop | LearningLoopWorkflow | 1 hour |
| daily-recommendations | DailyRecommendationWorkflow | 09:00 UTC |
| maintenance | MaintenanceWorkflow | 6 hours |

---

## Summary

| Category | Capabilities |
|----------|--------------|
| Video Ingestion | 9 |
| Decomposition | 7 |
| Idea Registry | 4 |
| Decision Engine | 8 |
| Hypothesis Factory | 4 |
| Knowledge Extraction | 5 |
| Metrics & Learning | 10 |
| Recommendations | 4 |
| Telegram Bot | 16 |
| Multi-Agent | 4 |
| Maintenance | 5 |
| API | 10 |
| **TOTAL** | **86** |

---

## Database Tables

### Core Pipeline
- `creatives` — Входящие видео
- `transcripts` — Транскрипты (AssemblyAI)
- `decomposed_creatives` — LLM-разбор
- `ideas` — Канонические идеи
- `decisions` — Решения DE
- `decision_traces` — Trace checks
- `hypotheses` — Сгенерированные гипотезы

### Modular System
- `module_bank` — Извлечённые модули
- `module_learnings` — Обучение модулей
- `premise_bank` — Narrative premises
- `premise_learnings` — Обучение premises

### Metrics & Learning
- `raw_metrics_current` — Live метрики
- `daily_metrics_snapshot` — Daily snapshots
- `outcome_aggregates` — Агрегированные outcomes
- `component_learnings` — По компонентам
- `avatar_learnings` — По аватарам

### Buyer System
- `buyers` — Зарегистрированные buyers
- `buyer_interactions` — Лог сообщений

### Multi-Agent
- `agent_tasks` — Task queue

---

## Related Documents

- `docs/TEMPORAL_WORKFLOWS.md` — Workflow reference
- `docs/TEMPORAL_RUNBOOK.md` — Operations guide
- `docs/SCHEMA_REFERENCE.md` — Database schema
- `docs/API_REFERENCE.md` — API endpoints
