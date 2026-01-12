# Backlog Analyzer

Анализ открытых issues GitHub: приоритизация и определение параллельных задач.

## Использование

```
/backlog              — полный анализ backlog
/backlog quick        — только top-5 приоритетных
/backlog parallel     — только группы параллельных задач
```

## Действие

### 1. Получить все открытые issues

```bash
gh issue list --state open --json number,title,labels,body,createdAt,updatedAt --limit 50
```

### 2. Для каждого issue извлечь метаданные

- **Priority** (из labels или контекста):
  - `priority:critical` / `critical` → P0
  - `priority:high` / `bug` → P1
  - `priority:medium` / `enhancement` → P2
  - Остальные → P3

- **Process** (из title/body/labels):
  - `decision-engine` / `DE` → process:de
  - `learning-loop` / `learning` → process:ll
  - `hypothesis-factory` / `hypothesis` → process:hf
  - `video-ingestion` / `video` / `temporal` → process:vi
  - `keitaro` / `metrics` → process:kt
  - `telegram` / `notification` → process:tg
  - `schema` / `migration` / `DB` → process:db

- **Complexity** (эвристика):
  - Слова: "refactor", "architecture", "redesign" → high
  - Слова: "add", "fix", "update" → medium
  - Слова: "typo", "docs", "rename" → low

- **Dependencies**:
  - Искать паттерны: `depends on #N`, `after #N`, `blocked by #N`
  - Извлечь номера зависимых issues

- **Files touched** (если указаны в body):
  - Искать паттерны путей: `decision-engine-service/`, `infrastructure/`, etc.

### 3. Построить граф зависимостей

```
Issue #X depends on #Y → X не начинать пока Y не закрыт
```

Использовать топологическую сортировку для определения порядка.

### 4. Определить параллельные группы

Правила совместимости (можно параллельно):
| Process A | Process B | Parallel? |
|-----------|-----------|-----------|
| de | ll | YES |
| de | hf | NO (общий код) |
| ll | kt | YES |
| vi | tg | YES |
| db | * | NO (migrations first) |

Issues параллельны если:
- Разные processes (по таблице выше)
- Нет прямых зависимостей
- Не затрагивают одни файлы

### 5. Выход — структурированный отчёт

```markdown
## Backlog Analysis

### Priority Queue (в порядке выполнения)

| # | Issue | Priority | Process | Complexity | Blocked By |
|---|-------|----------|---------|------------|------------|
| 1 | #123 Title | P0 | de | high | - |
| 2 | #125 Title | P1 | ll | medium | - |
| 3 | #127 Title | P1 | hf | medium | #123 |

### Parallel Execution Groups

**Group A** (можно запускать сейчас):
- #123 (de) — Agent 1
- #125 (ll) — Agent 2
- #130 (tg) — Agent 3

**Group B** (после Group A):
- #127 (hf) — blocked by #123
- #128 (vi) — blocked by #125

### Recommendations

1. **Immediate Start**: #123, #125, #130 (3 agents parallel)
2. **Quick Wins**: #131 (docs), #132 (typo) — low effort
3. **Blocked**: #127 waiting for #123

### Warnings

- #140: No process detected, needs triage
- #145: High complexity, consider splitting
```

## Вспомогательные команды

После анализа можно:

```bash
# Взять конкретный issue
./scripts/task-start.sh 123

# Назначить агентам
./scripts/agent-add-task.sh 123  # Agent 1
./scripts/agent-add-task.sh 125  # Agent 2
```

## Интеграция с Multi-Agent

Если запущено N агентов:

```bash
# Показать какой агент что делает
gh issue list --state open --json number,assignees --jq '.[] | select(.assignees | length > 0)'
```

Рекомендации учитывают текущую загрузку агентов.

## Пример вывода

```
/backlog

📊 Backlog Analysis (12 open issues)

## Priority Queue

| Rank | Issue | Title | P | Process | Est |
|------|-------|-------|---|---------|-----|
| 1 | #401 | Fix hypothesis stuck | P1 | hf | M |
| 2 | #403 | Add Keitaro polling | P2 | kt | M |
| 3 | #405 | Refactor DE checks | P2 | de | H |

## Parallel Groups

🟢 **Start Now** (no dependencies):
  • #401 (hf) + #403 (kt) + #408 (tg)

🟡 **After Group 1**:
  • #405 (de) — waiting for #401

🔴 **Blocked**:
  • #410 — depends on #405

## Quick Wins (< 30 min):
  • #412 (docs)
  • #413 (typo fix)

💡 Recommendation: Start 3 agents on #401, #403, #408
```
