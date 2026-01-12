# Backlog

Расставить лейблы `queue-1`, `queue-2`, `queue-3`... на issues по приоритету.

## Использование

```
/backlog        — расставить лейблы
/backlog show   — показать очередь (без изменений)
```

## Действие

### 1. Получить issues

```bash
gh issue list --state open --json number,title,labels,createdAt --limit 30
```

### 2. Определить приоритет

| Лейбл/признак | Приоритет |
|---------------|-----------|
| `critical` | Высший |
| `bug` | Высокий |
| `enhancement` | Средний |
| Старые (>7 дней) | +1 к приоритету |

### 3. Расставить лейблы

```bash
# Создать лейблы (один раз)
gh label create "queue-1" --color "FF0000" --force
gh label create "queue-2" --color "FF6600" --force
gh label create "queue-3" --color "FFCC00" --force
gh label create "queue-4" --color "99CC00" --force
gh label create "queue-5" --color "33CC33" --force

# Для каждого issue по приоритету
gh issue edit {N} --remove-label "queue-1,queue-2,queue-3,queue-4,queue-5"
gh issue edit {N} --add-label "queue-{позиция}"
```

## Вывод

```
## Очередь задач

1. #401 — Fix critical bug (critical)
2. #403 — Add validation (bug)
3. #405 — Update docs (enhancement)

Лейблы обновлены ✓
```

## Показать очередь

```bash
gh issue list --state open --json number,title,labels --jq '.[] | select(.labels | map(.name) | any(startswith("queue-")))' | jq -s 'sort_by(.labels | map(.name) | map(select(startswith("queue-")))[0])'
```
