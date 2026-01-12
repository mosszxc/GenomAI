# Backlog

Расставить очередь задач для параллельных агентов.

## Использование

```
/backlog        — расставить очередь + показать что можно параллельно
/backlog show   — только показать (без изменений)
```

## Лейблы

| Лейбл | Что значит |
|-------|------------|
| `queue-1` | Первая задача |
| `queue-2` | Вторая задача |
| `queue-3` | Третья задача |
| `parallel` | Можно делать одновременно с другими `parallel` |

## Действие

### 1. Получить issues

```bash
gh issue list --state open --json number,title,labels,body,createdAt --limit 30
```

### 2. Найти зависимости

Искать в body: `blocked by #N`, `depends on #N`, `after #N`

### 3. Определить приоритет

`critical` → `bug` → `enhancement` → по дате

### 4. Расставить лейблы

- `queue-N` — позиция в очереди
- `parallel` — если нет зависимостей от других открытых issues

### 5. Создать лейблы

```bash
gh label create "queue-1" --color "FF0000" --force
gh label create "queue-2" --color "FF6600" --force
gh label create "queue-3" --color "FFCC00" --force
gh label create "parallel" --color "0E8A16" --force
```

## Вывод

```
## Очередь

| # | Issue | Parallel? |
|---|-------|-----------|
| 1 | #401 Fix bug | ✅ |
| 2 | #403 Add feature | ✅ |
| 3 | #405 Refactor | ✅ |
| 4 | #407 Update X | ❌ (ждёт #401) |

## Можно взять сейчас (3 агента)

- Agent 1 → #401
- Agent 2 → #403
- Agent 3 → #405

#407 заблокирован — ждёт #401
```
