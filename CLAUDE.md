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

## Релизы (ОБЯЗАТЕЛЬНО при деплое)

При каждом деплое создавать **и git tag, и GitHub Release**.

**Версионирование:** semver `vMAJOR.MINOR.PATCH`
- MAJOR: breaking changes
- MINOR: новые фичи
- PATCH: багфиксы

**Git tag (аннотированный):**
```bash
git tag -a v1.2.3 -m "$(cat <<'EOF'
v1.2.3

## Что нового
- feat: краткое описание (#issue)
- fix: краткое описание (#issue)

## Изменения
- Затронутые компоненты
EOF
)"
git push origin v1.2.3
```

**GitHub Release:**
```bash
gh release create v1.2.3 --title "v1.2.3 — Краткое название" --notes "$(cat <<'EOF'
## 🚀 Что нового

Краткое описание для пользователя — что улучшилось.

## ✨ Features
- Описание фичи (#123)

## 🐛 Fixes
- Описание фикса (#124)

## 📦 Other
- Рефакторинг, docs, тесты
EOF
)"
```

**Чеклист перед релизом:**
1. `make test` — тесты проходят
2. `develop` смержен в `main`
3. Собраны все issues с последнего релиза
4. Changelog сгруппирован по типам

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

## Test-First (когда критично)

**Тест СНАЧАЛА обязателен для:**
- Багфиксы — сначала тест воспроизводящий баг, потом фикс
- Регрессии — тест на старое поведение перед изменением
- Edge cases — граничные условия (null, empty, overflow)

**Можно без теста сначала:**
- Прототипы и эксперименты
- Конфиги и миграции
- Простые рефакторинги (rename, move)

**Формат:**
1. Написать failing test
2. Убедиться что падает по правильной причине
3. Написать минимальный код для прохождения
4. Рефакторинг если нужно

## Systematic Debugging

**Правило: НЕ ФИКСИТЬ без понимания причины.**

### Фаза 1: Расследование
1. Прочитать ошибку полностью (stack trace, line numbers)
2. Воспроизвести стабильно
3. `git diff` — что менялось недавно?
4. Добавить логи на границах компонентов
5. Трассировать данные назад по call stack

### Фаза 2: Анализ паттернов
1. Найти похожий работающий код
2. Задокументировать ВСЕ различия
3. Проверить зависимости и env

### Фаза 3: Гипотеза
1. Сформулировать явную гипотезу: "Баг потому что X"
2. Тестировать ОДНО изменение за раз
3. Гипотеза не подтвердилась → новая гипотеза

### Фаза 4: Фикс
1. Failing test на баг
2. Минимальный фикс root cause
3. Тест зелёный

**СТОП-сигналы (начать сначала):**
- Предлагаешь фикс без понимания причины
- "Быстрый фикс, потом разберёмся"
- Несколько изменений одновременно
- 3+ фикса не работают → проблема архитектурная

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
