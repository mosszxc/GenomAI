# CLAUDE.md

Short, dense. Lists > prose.

## Project
**GenomAI** — Autonomous Creative Decision System. Market = ground truth. LLM: transcripts only.

## Stack
DB: Supabase `genomai` schema, project `ftrerelppsnbdcmtcwya`
Backend: FastAPI `decision-engine-service/`, genomai.onrender.com:10000
Orchestration: Temporal | Tracking: Keitaro | UI: Telegram

## Workflow (develop branch)
```bash
# 1. Старт задачи (ветка из develop)
./scripts/task-start.sh <issue-number>

# 2. Работа в worktree + локальный сервер

# 3. Завершение → PR в develop
./scripts/task-done.sh <issue-number>

# 4. Deploy (по требованию)
./scripts/deploy.sh  # develop → main → Render
```

## Локальная разработка
```bash
make up     # Утром: запустить всё (Temporal + Worker + FastAPI)
make down   # Вечером: остановить всё
```

## Тестирование
```bash
make test          # Critical tests (~15s)
make test-unit     # All unit tests (~45s)
make ci            # Full CI simulation
```

**qa-notes обязательны:** `qa-notes/issue-XXX-*.md`

## Schema
Таблицы: `ideas`, `decisions`, `decomposed_creatives`
Референс: `docs/SCHEMA_REFERENCE.md`

**Проверить перед работой с БД:**
```sql
SELECT column_name, data_type, is_generated
FROM information_schema.columns
WHERE table_schema = 'genomai' AND table_name = 'table_name';
```

## Reference by Task Type
| Задача | Документ |
|--------|----------|
| Temporal | `docs/TEMPORAL_WORKFLOWS.md` |
| DB schema | `docs/SCHEMA_REFERENCE.md` |
| API | `docs/API_REFERENCE.md` |
| Lessons | `grep -i "keyword" LESSONS.md` |

## Git
- Feature ветки из `develop`
- PR в `develop` (накапливается)
- Deploy: `develop → main` по требованию
- Коммит делается автоматически, не спрашивать

## Env
`SUPABASE_URL` `SUPABASE_SERVICE_ROLE_KEY` `API_KEY`

## API
POST `/api/decision/` | POST `/learning/process` | GET `/health`

## Temporal Workflows
| Workflow | Schedule |
|----------|----------|
| KeitaroPollerWorkflow | Every 1 hour |
| LearningLoopWorkflow | Child of KeitaroPoller |
| DailyRecommendationWorkflow | 09:00 UTC |
| MaintenanceWorkflow | Every 6 hours |

```bash
python -m temporal.schedules list
python -m temporal.schedules trigger <schedule-id>
```

## Rules
1. Market = truth
2. Deterministic + traceable
3. Schema-first (проверь колонки перед кодом)
4. qa-notes обязательны

## Перед завершением issue (ОБЯЗАТЕЛЬНО)

**Тест конкретного функционала issue:**
1. Понять что именно должно работать
2. Написать curl/запрос который проверяет ЭТУ функцию
3. Выполнить на localhost
4. Убедиться что работает

**Пример для issue "валидация --geo":**
```bash
# Невалидный geo должен отклоняться
curl localhost:10000/endpoint --data '{"geo": "INVALID"}'
# Ожидаем: 400 Bad Request

# Валидный geo должен приниматься
curl localhost:10000/endpoint --data '{"geo": "US"}'
# Ожидаем: 200 OK
```

**После теста:** `./scripts/task-done.sh <N>`

## Dirs
`decision-engine-service/` `infrastructure/migrations/` `docs/`
