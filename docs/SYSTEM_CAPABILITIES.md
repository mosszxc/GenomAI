# GenomAI System Capabilities

Полный список функциональных возможностей системы для тестирования.

**Последнее обновление**: 2025-12-26

---

## 1. VIDEO INGESTION (sphere:ingestion)

### 1.1 Приём видео
| ID | Capability | Проверка | Статус |
|----|------------|----------|--------|
| ING-01 | Buyer отправляет видео в Telegram | Видео сохраняется в `creatives` | MVP |
| ING-02 | Buyer отправляет ссылку на видео в Telegram | URL парсится, видео скачивается | MVP |
| ING-03 | Создание записи creative с buyer_id | `creatives.buyer_id` заполнен | MVP |
| ING-04 | Дедупликация по video_url | Повторная ссылка не создаёт дубликат | MVP |
| ING-05 | Event: CreativeReceived | Запись в `event_log` | MVP |

### 1.2 Транскрипция
| ID | Capability | Проверка | Статус |
|----|------------|----------|--------|
| ING-10 | Транскрипция через AssemblyAI | `transcripts` запись создана | MVP |
| ING-11 | Связь transcript → creative | `transcripts.creative_id` = creative.id | MVP |
| ING-12 | Event: TranscriptCreated | Запись в `event_log` | MVP |
| ING-13 | Ошибка транскрипции | Статус creative обновляется, уведомление | MVP |

### 1.3 Workflows
- `Creative Transcription` (WMnFHqsFh8i7ddjV)
- `Buyer Creative Registration` (d5i9dB2GNqsbfmSD)

---

## 2. DECOMPOSITION (sphere:decomposition)

### 2.1 LLM-разбор
| ID | Capability | Проверка | Статус |
|----|------------|----------|--------|
| DEC-01 | LLM извлекает 14 полей из транскрипта | Все required fields в payload | MVP |
| DEC-02 | Валидация output против JSON Schema | `/api/schema/validate` возвращает valid:true | MVP |
| DEC-03 | Создание decomposed_creative | Запись в `decomposed_creatives` | MVP |
| DEC-04 | Связь с creative и idea | FK заполнены корректно | MVP |
| DEC-05 | Event: CreativeDecomposed | Запись в `event_log` | MVP |

### 2.2 Schema Validation
| ID | Capability | Проверка | Статус |
|----|------------|----------|--------|
| DEC-10 | Валидация v1 schema (14 fields) | MISSING_REQUIRED_FIELD при пропуске | MVP |
| DEC-11 | Валидация enum values | INVALID_ENUM_VALUE при неверном значении | MVP |
| DEC-12 | Поддержка v2 schema | v2 принимается с optional fields | MVP |

### 2.3 Canonical Fields (v1)
```
angle_type, core_belief, promise_type, emotion_primary,
emotion_intensity, message_structure, opening_type,
state_before, state_after, context_frame, source_type,
risk_level, horizon, schema_version
```

### 2.4 Workflows
- `creative_decomposition_llm` (mv6diVtqnuwr7qev)

---

## 3. IDEA REGISTRY (sphere:idea-registry)

### 3.1 Создание идей
| ID | Capability | Проверка | Статус |
|----|------------|----------|--------|
| IDR-01 | Создание idea из decomposed_creative | Запись в `ideas` | MVP |
| IDR-02 | Генерация canonical_hash | Уникальный hash в `ideas.canonical_hash` | MVP |
| IDR-03 | Идемпотентность по hash | Повторный payload не создаёт дубликат | MVP |
| IDR-04 | Начальный статус = 'active' | `ideas.status = 'active'` | MVP |
| IDR-05 | death_state = 'alive' | `ideas.death_state = 'alive'` | MVP |
| IDR-06 | Event: IdeaCreated | Запись в `event_log` | MVP |

### 3.2 API
| ID | Capability | Проверка | Статус |
|----|------------|----------|--------|
| IDR-10 | POST /api/idea-registry/register | Возвращает idea_id, canonical_hash | MVP |
| IDR-11 | Связь idea → avatar | avatar_id заполнен если определён | MVP |

### 3.3 Workflows
- `idea_registry_create` (cGSyJPROrkqLVHZP)

---

## 4. DECISION ENGINE (sphere:decision-engine)

### 4.1 Decision Flow
| ID | Capability | Проверка | Статус |
|----|------------|----------|--------|
| DE-01 | POST /api/decision/ принимает idea_id | Возвращает decision + trace | MVP |
| DE-02 | 4 проверки выполняются последовательно | trace.checks содержит 4 записи | MVP |
| DE-03 | Первый failed check останавливает цепочку | Остальные checks не выполняются | MVP |
| DE-04 | Decision сохраняется в `decisions` | Append-only запись | MVP |
| DE-05 | Trace сохраняется в `decision_traces` | Детали всех checks | MVP |
| DE-06 | Event: DecisionMade | Запись в `event_log` | MVP |

### 4.2 CHECK 1: Schema Validity
| ID | Capability | Проверка | Статус |
|----|------------|----------|--------|
| DE-10 | Проверка наличия id, canonical_hash, status | PASSED если все есть | MVP |
| DE-11 | REJECT при отсутствии полей | decision_type = 'reject', reason = 'schema_invalid' | MVP |

### 4.3 CHECK 2: Death Memory
| ID | Capability | Проверка | Статус |
|----|------------|----------|--------|
| DE-20 | Проверка idea.status != 'dead' | PASSED если не dead | MVP |
| DE-21 | REJECT при dead idea | decision_type = 'reject', reason = 'idea_dead' | MVP |
| DE-22 | Проверка cluster death | REJECT если кластер мёртв | Future |

### 4.4 CHECK 3: Fatigue Constraint
| ID | Capability | Проверка | Статус |
|----|------------|----------|--------|
| DE-30 | MVP: всегда PASS | result = 'PASSED', note = 'MVP not implemented' | MVP |
| DE-31 | Full: проверка fatigue_level vs angle | REJECT при высоком fatigue + low novelty | Future |

### 4.5 CHECK 4: Risk Budget
| ID | Capability | Проверка | Статус |
|----|------------|----------|--------|
| DE-40 | Проверка active_ideas_count < max | PASSED если есть слоты | MVP |
| DE-41 | DEFER при превышении лимита | decision_type = 'defer', reason = 'risk_budget_exceeded' | MVP |
| DE-42 | Default max_active_ideas = 100 | Лимит по умолчанию | MVP |

### 4.6 Decision Types
| Type | Условие | Следующий шаг |
|------|---------|---------------|
| APPROVE | Все 4 checks PASSED | → Hypothesis Factory |
| REJECT | Check 1, 2, или 3 FAILED | Идея не используется |
| DEFER | Check 4 FAILED | Повторить позже |

### 4.7 Workflows
- `decision_engine_mvp` (YT2d7z5h9bPy1R4v)
- `keep_alive_decision_engine` (ClXUPP2IvWRgu99y)

---

## 5. HYPOTHESIS FACTORY (sphere:hypothesis-factory)

### 5.1 Генерация гипотез
| ID | Capability | Проверка | Статус |
|----|------------|----------|--------|
| HF-01 | Создание hypothesis из approved idea | Запись в `hypotheses` | MVP |
| HF-02 | Связь hypothesis → idea, decision | FK заполнены | MVP |
| HF-03 | Статус = 'pending' | `hypotheses.status = 'pending'` | MVP |
| HF-04 | Event: HypothesisCreated | Запись в `event_log` | MVP |

### 5.2 Workflows
- `hypothesis_factory_generate` (oxG1DqxtkTGCqLZi)

---

## 6. DELIVERY (sphere:delivery)

### 6.1 Telegram Delivery
| ID | Capability | Проверка | Статус |
|----|------------|----------|--------|
| DEL-01 | Отправка hypothesis buyer'у | Сообщение в Telegram | MVP |
| DEL-02 | Форматирование с компонентами | Читаемый формат с % confidence | MVP |
| DEL-03 | Запись в `deliveries` | Append-only лог доставок | MVP |
| DEL-04 | Event: HypothesisDelivered | Запись в `event_log` | MVP |

### 6.2 Recommendation Delivery
| ID | Capability | Проверка | Статус |
|----|------------|----------|--------|
| DEL-10 | Отправка recommendation buyer'у | Сообщение в Telegram | MVP |
| DEL-11 | Указание типа (exploit/explore) | Видно в сообщении | MVP |
| DEL-12 | Указание целевого аватара | Имя и desire аватара | MVP |

### 6.3 Workflows
- `Telegram Hypothesis Delivery` (5q3mshC9HRPpL6C0)
- `Recommendation Delivery` (QC8bmnAYdH5mkntG)

---

## 7. RECOMMENDATIONS (sphere:hypothesis-factory)

### 7.1 Генерация рекомендаций
| ID | Capability | Проверка | Статус |
|----|------------|----------|--------|
| REC-01 | POST /recommendations/generate | Возвращает recommendation с компонентами | MVP |
| REC-02 | 75% exploitation mode | Проверенные компоненты с высоким confidence | MVP |
| REC-03 | 25% exploration mode | Thompson Sampling для новых комбинаций | MVP |
| REC-04 | Фильтрация по buyer, geo, vertical | Релевантные рекомендации | MVP |

### 7.2 Lifecycle
| ID | Capability | Проверка | Статус |
|----|------------|----------|--------|
| REC-10 | GET /recommendations/ | Список pending рекомендаций | MVP |
| REC-11 | GET /recommendations/{id} | Получение рекомендации по ID | MVP |
| REC-12 | POST /{id}/executed | Привязка к creative_id | MVP |
| REC-13 | POST /{id}/outcome | Запись результата | MVP |
| REC-14 | GET /recommendations/stats | Статистика для мониторинга | MVP |

### 7.3 Future
| ID | Capability | Проверка | Статус |
|----|------------|----------|--------|
| REC-20 | Настройка exploit/explore ratio | API для изменения 75/25 | Future |

---

## 8. METRICS (sphere:metrics)

### 8.1 Keitaro Polling
| ID | Capability | Проверка | Статус |
|----|------------|----------|--------|
| MET-01 | Периодический polling Keitaro API | Данные в `raw_metrics_current` | MVP |
| MET-02 | creative_id = campaign_id в Keitaro | 1:1 mapping | MVP |
| MET-03 | Сбор: clicks, conversions, spend, revenue | Все поля заполнены | MVP |
| MET-04 | Event: RawMetricsObserved | Запись в `event_log` | MVP |

### 8.2 Snapshots
| ID | Capability | Проверка | Статус |
|----|------------|----------|--------|
| MET-10 | Создание daily snapshot | Запись в `daily_metrics_snapshot` | MVP |
| MET-11 | Immutable snapshots | UPDATE/DELETE запрещены | MVP |
| MET-12 | Event: DailyMetricsSnapshotCreated | Запись в `event_log` | MVP |

### 8.3 Workflows
- `Keitaro Poller` (0TrVJOtHiNEEAsTN)
- `Snapshot Creator` (Gii8l2XwnX43Wqr4)

---

## 9. OUTCOMES (sphere:outcomes)

### 9.1 Outcome Processing
| ID | Capability | Проверка | Статус |
|----|------------|----------|--------|
| OUT-01 | Обработка raw metrics в outcomes | Запись в `outcome_aggregates` | MVP |
| OUT-02 | Расчёт CPA = spend/conversions | CPA заполнен корректно | MVP |
| OUT-03 | environment_ctx с geo, vertical | JSONB заполнен | MVP |
| OUT-04 | origin_type = 'system' для realtime | Отличие от historical | MVP |

### 9.2 Aggregation API
| ID | Capability | Проверка | Статус |
|----|------------|----------|--------|
| OUT-10 | POST /api/outcomes/aggregate | Агрегация outcomes | MVP |
| OUT-11 | outcome_service.py | Логика агрегации в Python | MVP |

### 9.3 Workflows
- `Outcome Processor` (bbbQC4Aua5E3SYSK)
- `Outcome Aggregator` (243QnGrUSDtXLjqU)

---

## 10. LEARNING (sphere:learning)

### 10.1 Confidence Updates
| ID | Capability | Проверка | Статус |
|----|------------|----------|--------|
| LRN-01 | POST /learning/process | Обработка unprocessed outcomes | MVP |
| LRN-02 | CPA < 20 → confidence +0.1 | Положительный сигнал | MVP |
| LRN-03 | CPA >= 20 → confidence -0.15 | Отрицательный сигнал | MVP |
| LRN-04 | Time decay (exponential) | Старые данные меньше влияют | MVP |
| LRN-05 | Environment weighting | Контекст влияет на delta | MVP |
| LRN-06 | Версионирование confidence | Append в `idea_confidence_versions` | MVP |

### 10.2 Death Detection
| ID | Capability | Проверка | Статус |
|----|------------|----------|--------|
| LRN-10 | 3 consecutive failures → soft_dead | death_state обновляется | MVP |
| LRN-11 | 5 consecutive failures → hard_dead | death_state обновляется | MVP |
| LRN-12 | Death блокирует будущие decisions | Check 2 возвращает REJECT | MVP |

### 10.3 Component Learning
| ID | Capability | Проверка | Статус |
|----|------------|----------|--------|
| LRN-20 | Запись в component_learnings | По каждому компоненту | MVP |
| LRN-21 | Агрегация в avatar_learnings | winning_rate, sample_count | MVP |
| LRN-22 | Использование в recommendations | Высокий winning_rate → exploit | MVP |

### 10.4 API
| ID | Capability | Проверка | Статус |
|----|------------|----------|--------|
| LRN-30 | GET /learning/status | pending_outcomes count | MVP |

### 10.5 Workflows
- `Learning Loop v2` (fzXkoG805jQZUR3S)

---

## 11. BUYER SYSTEM (sphere:buyer)

### 11.1 Onboarding
| ID | Capability | Проверка | Статус |
|----|------------|----------|--------|
| BUY-01 | /start → State machine | 5 состояний онбординга | MVP |
| BUY-02 | Сбор: name, geos[], verticals[], keitaro_source | Все поля в `buyers` | MVP |
| BUY-03 | Multi-geo support | geos как TEXT[] | MVP |
| BUY-04 | Multi-vertical support | verticals как TEXT[] | MVP |
| BUY-05 | State persistence | `buyer_states` таблица | MVP |

### 11.2 Commands
| ID | Capability | Проверка | Статус |
|----|------------|----------|--------|
| BUY-10 | /start | Начало онбординга | MVP |
| BUY-11 | /stats | Статистика buyer'а | MVP |
| BUY-12 | /help | Справка (работает всегда) | MVP |

### 11.3 Interaction Logging
| ID | Capability | Проверка | Статус |
|----|------------|----------|--------|
| BUY-20 | Все сообщения логируются | Append в `buyer_interactions` | MVP |
| BUY-21 | direction: 'in' / 'out' | Входящие и исходящие | MVP |
| BUY-22 | message_type classification | text, video, command, etc. | MVP |

### 11.4 Daily Digest
| ID | Capability | Проверка | Статус |
|----|------------|----------|--------|
| BUY-30 | Ежедневная сводка в Telegram | Автоматическая отправка | MVP |

### 11.5 Workflows
- `Telegram Router` (BuyQncnHNb7ulL6z)
- `Buyer Onboarding` (hgTozRQFwh4GLM0z)
- `Buyer Creative Registration` (d5i9dB2GNqsbfmSD)
- `Buyer Stats Command` (rHuT8dYyIXoiHMAV)
- `Buyer Daily Digest` (WkS1fPSxZaLmWcYy)
- `Buyer Test Conclusion Checker` (4uluD04qYHhsetBy)

---

## 12. HISTORICAL IMPORT

### 12.1 Import Flow
| ID | Capability | Проверка | Статус |
|----|------------|----------|--------|
| HIS-01 | Batch URL input через Telegram | Парсинг множества ссылок | MVP |
| HIS-02 | Queue management | `historical_import_queue` | MVP |
| HIS-03 | origin_type = 'historical' | Отличие от realtime | MVP |
| HIS-04 | Связь с buyer через keitaro_source | Mapping по source ID | MVP |

### 12.2 Workflows
- `Historical Creative Import` (1FC7amTd3dCRZPEa)
- `Buyer Historical Loader` (lmiWkYTRZPSpydJH)
- `Buyer Historical URL Handler` (A8gKvO5810L1lusZ)
- `Historical Import Video Handler` (UYgvqpsU3TMzb2Qd)

---

## 13. INFRASTRUCTURE

### 13.1 Health & Monitoring
| ID | Capability | Проверка | Статус |
|----|------------|----------|--------|
| INF-01 | GET /health | status: 'ok' | MVP |
| INF-02 | Keep-alive ping каждые 10 мин | Cold start prevention | MVP |
| INF-03 | Retry logic (3x15s) | Обработка 503 после cold start | MVP |

### 13.2 Event Log
| ID | Capability | Проверка | Статус |
|----|------------|----------|--------|
| INF-10 | Все события в event_log | Append-only audit trail | MVP |
| INF-11 | Immutable (no UPDATE/DELETE) | Trigger protection | MVP |

### 13.3 Database Constraints
| ID | Capability | Проверка | Статус |
|----|------------|----------|--------|
| INF-20 | Generated columns read-only | win_rate, avg_roi не пишутся | MVP |
| INF-21 | FK constraints | Referential integrity | MVP |
| INF-22 | CHECK constraints | origin_type + decision_id rules | MVP |

---

## 14. ERROR HANDLING

### 14.1 API Errors
| ID | Capability | Проверка | Статус |
|----|------------|----------|--------|
| ERR-01 | 400 Bad Request | Невалидный payload | MVP |
| ERR-02 | 401 Unauthorized | Отсутствует/неверный API_KEY | MVP |
| ERR-03 | 404 Not Found | idea_id не существует | MVP |
| ERR-04 | 500 Internal Error | Unhandled exception | MVP |

### 14.2 n8n Error Handling
| ID | Capability | Проверка | Статус |
|----|------------|----------|--------|
| ERR-10 | Error workflow trigger | Уведомление при ошибке | MVP |
| ERR-11 | continueOnFail на критических нодах | Graceful degradation | MVP |

---

## 15. SECURITY

### 15.1 Authentication
| ID | Capability | Проверка | Статус |
|----|------------|----------|--------|
| SEC-01 | Bearer token на всех endpoints (кроме /health) | 401 без токена | MVP |
| SEC-02 | Service role key для Supabase | Не anon key | MVP |

### 15.2 Data Protection
| ID | Capability | Проверка | Статус |
|----|------------|----------|--------|
| SEC-10 | Credentials не в коде | Environment variables | MVP |
| SEC-11 | genomai schema isolation | Не public schema | MVP |

---

## Summary

| Sphere | MVP Capabilities | Future | Total |
|--------|------------------|--------|-------|
| Ingestion | 13 | 0 | 13 |
| Decomposition | 12 | 0 | 12 |
| Idea Registry | 8 | 0 | 8 |
| Decision Engine | 16 | 2 | 18 |
| Hypothesis Factory | 4 | 0 | 4 |
| Delivery | 7 | 0 | 7 |
| Recommendations | 9 | 1 | 10 |
| Metrics | 8 | 0 | 8 |
| Outcomes | 6 | 0 | 6 |
| Learning | 14 | 0 | 14 |
| Buyer | 14 | 0 | 14 |
| Historical | 4 | 0 | 4 |
| Infrastructure | 8 | 0 | 8 |
| Error Handling | 6 | 0 | 6 |
| Security | 4 | 0 | 4 |
| **TOTAL** | **123** | **3** | **126** |

---

## Open Questions (TBD)

1. **Death Memory**: Как определяется cluster для cluster death?
2. **Fatigue Check**: Threshold values для full implementation
3. **Thompson Sampling**: Параметры alpha/beta priors
4. **Telegram**: Дополнительные команды кроме /start, /stats, /help?

---

## Database Tables (genomai schema)

### Core Pipeline
| Таблица | Назначение | Mutable | Writer |
|---------|-----------|---------|--------|
| `creatives` | Входящие видео-креативы | Yes (status) | Buyer Registration |
| `transcripts` | Транскрипты (AssemblyAI) | No | Transcription |
| `decomposed_creatives` | LLM-разбор структуры | No | Decomposition |
| `ideas` | Канонические идеи | Yes (death_state) | Idea Registry, Learning |
| `decisions` | Решения DE (append-only) | No | Decision Engine |
| `decision_traces` | Trace checks | No | Decision Engine |
| `hypotheses` | Сгенерированные гипотезы | Yes (status) | Hypothesis Factory |
| `deliveries` | Лог доставок | No | Telegram Delivery |
| `recommendations` | Рекомендации для buyers | Yes | Recommendation Engine |

### Metrics & Outcomes
| Таблица | Назначение | Mutable | Writer |
|---------|-----------|---------|--------|
| `raw_metrics_current` | Live метрики из Keitaro | Yes | Keitaro Poller |
| `daily_metrics_snapshot` | Daily snapshots | No | Snapshot Creator |
| `outcome_aggregates` | Агрегированные outcomes | Yes (learning_applied) | Outcome Aggregator |

### Learning
| Таблица | Назначение | Mutable | Writer |
|---------|-----------|---------|--------|
| `idea_confidence_versions` | История confidence | No | Learning Loop |
| `fatigue_state_versions` | История fatigue | No | Learning Loop |
| `component_learnings` | Learnings по компонентам | Yes | Learning Loop |
| `avatar_learnings` | Learnings по аватарам | Yes | Learning Loop |
| `exploration_log` | Thompson Sampling tracking | No | Recommendation Engine |

### Buyer System
| Таблица | Назначение | Mutable | Writer |
|---------|-----------|---------|--------|
| `buyers` | Зарегистрированные buyers | Yes | Onboarding |
| `buyer_states` | State machine онбординга | Yes | Onboarding |
| `buyer_interactions` | Лог Telegram сообщений | No | Telegram Router |
| `historical_import_queue` | Очередь импорта | Yes | Historical Import |

### Config & Lookup
| Таблица | Назначение | Mutable | Writer |
|---------|-----------|---------|--------|
| `config` | Системная конфигурация | Yes | Manual |
| `keitaro_config` | Keitaro credentials | Yes | Manual |
| `avatars` | Целевые аватары | Yes | Manual |
| `event_log` | Audit trail (append-only) | No | All workflows |
| `geo_lookup` | Нормализация geo | Yes | Manual |
| `vertical_lookup` | Нормализация verticals | Yes | Manual |

---

## Related Documents

- `docs/SCHEMA_REFERENCE.md` — Database schema
- `docs/API_REFERENCE.md` — API endpoints
- `docs/N8N_WORKFLOWS.md` — All 23 workflows
- `infrastructure/schemas/` — JSON Schemas
