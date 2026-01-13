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
| MetricsProcessingWorkflow | Every 1 hour (+child) |
| LearningLoopWorkflow | Every 1 hour (+child) |
| DailyRecommendationWorkflow | 09:00 UTC |
| MaintenanceWorkflow | Every 6 hours |
| HealthCheckWorkflow | Every 3 hours |

```bash
python -m temporal.schedules list
python -m temporal.schedules trigger <schedule-id>
```

## Rules
1. Market = truth
2. Deterministic + traceable
3. Schema-first (проверь колонки перед кодом)
4. qa-notes обязательны

## qa-notes с тестом (ОБЯЗАТЕЛЬНО)

Создать `qa-notes/issue-XXX-*.md` с секцией `## Test`:

```markdown
## Что изменено
- Добавлена валидация --geo флага

## Test
\`\`\`bash
curl -sf localhost:10000/endpoint -d '{"geo": "INVALID"}' || echo "OK: rejected"
\`\`\`
```

**task-done.sh автоматически:**
1. Находит qa-notes
2. Парсит команду из `## Test` → `\`\`\`bash`
3. Выполняет на localhost
4. exit code != 0 → стоп

## Issue Closure Report (ПОКАЗАТЬ ПОЛЬЗОВАТЕЛЮ)

**⚠️ ВАЖНО: Показывать отчёт ТОЛЬКО после:**
1. `./scripts/task-done.sh <issue-number>` успешно выполнен
2. PR создан или коммит сделан

Отчёт = подтверждение ПОСЛЕ факта, не до.

```
═══════════════════════════════════════════════════════
ISSUE #XXX CLOSED
═══════════════════════════════════════════════════════

Проблема: <что было сломано/отсутствовало>
Решение: <что сделано>

FUNCTIONAL TEST: PASSED
  Command: <команда из qa-notes>
  Result: <вывод>

qa-notes: qa-notes/issue-XXX-*.md
═══════════════════════════════════════════════════════
```

## Dirs
`decision-engine-service/` `infrastructure/migrations/` `docs/`

## Anti-Patterns (ЗАПРЕЩЕНО)

**Код ниже приводит к багам. НЕ писать так:**

```python
# ❌ ПЛОХО: Bare except глотает все ошибки
try:
    do_something()
except Exception:
    pass  # Баг: ошибка никогда не будет видна

# ✅ ХОРОШО: Специфичное исключение + логирование
try:
    do_something()
except SpecificError as e:
    logger.error(f"Failed: {e}")
    raise  # или handle gracefully
```

```python
# ❌ ПЛОХО: Доступ к списку без проверки
first_item = data[0]  # IndexError если пусто

# ✅ ХОРОШО: Проверка перед доступом
first_item = data[0] if data else None
# или
if not data:
    raise ValueError("Expected non-empty list")
first_item = data[0]
```

```python
# ❌ ПЛОХО: Деление без проверки
ratio = a / b  # ZeroDivisionError

# ✅ ХОРОШО: Защита от деления на ноль
ratio = a / b if b else 0
# или
ratio = a / max(b, 1)
```

```python
# ❌ ПЛОХО: Hardcoded URLs/credentials
url = "https://api.example.com/webhook"

# ✅ ХОРОШО: Из конфига или env
url = os.environ.get("WEBHOOK_URL")
```

**Temporal-специфичные:**
```python
# ❌ ПЛОХО: datetime в workflow (non-deterministic)
now = datetime.utcnow()

# ✅ ХОРОШО: workflow.now()
now = workflow.now()
```

**Проверка mypy:** `make mypy` (или в pre-commit)
