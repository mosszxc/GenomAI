# Backlog Priority Manager

Анализ и приоритизация issues через лейблы `queue-1`, `queue-2`, `queue-3`...

## Использование

```
/backlog              — анализ + расставить лейблы очередности
/backlog show         — только показать текущую очередь (без изменений)
/backlog reset        — убрать все queue-* лейблы
```

## Лейблы очередности

| Лейбл | Значение |
|-------|----------|
| `queue-1` | Делать первым |
| `queue-2` | Делать вторым |
| `queue-3` | Делать третьим |
| ... | ... |

## Действие

### 1. Получить все открытые issues

```bash
gh issue list --state open --json number,title,labels,body,createdAt --limit 50
```

### 2. Определить приоритет каждого issue

**Факторы (в порядке важности):**

1. **Критичность** (из labels):
   - `critical` / `priority:critical` → вес +100
   - `bug` / `priority:high` → вес +50
   - `enhancement` / `priority:medium` → вес +20
   - `docs` / `priority:low` → вес +5

2. **Блокеры** (из body/comments):
   - Паттерны: `blocks #N`, `required for #N` → вес +30
   - Паттерны: `blocked by #N`, `depends on #N` → вес -10 (если блокер открыт)

3. **Возраст**:
   - Старше 7 дней без активности → вес +10
   - Старше 14 дней → вес +20

4. **Сложность** (эвристика из title/body):
   - `refactor`, `architecture`, `redesign` → вес -5 (откладывать)
   - `typo`, `fix`, `quick` → вес +10 (быстрые победы)

### 3. Отсортировать по весу и назначить очередь

```python
sorted_issues = sorted(issues, key=lambda x: x['weight'], reverse=True)
for i, issue in enumerate(sorted_issues, 1):
    queue_label = f"queue-{i}"
```

### 4. Обновить лейблы в GitHub

```bash
# Убрать старые queue-* лейблы
gh issue edit {number} --remove-label "queue-1,queue-2,queue-3,queue-4,queue-5,queue-6,queue-7,queue-8,queue-9,queue-10"

# Добавить новый queue-* лейбл
gh issue edit {number} --add-label "queue-{N}"
```

### 5. Создать лейблы если не существуют

```bash
# Проверить существующие лейблы
gh label list --json name | jq -r '.[].name' | grep "^queue-"

# Создать недостающие (цвет по приоритету)
gh label create "queue-1" --color "FF0000" --description "Priority 1 - Do first" 2>/dev/null || true
gh label create "queue-2" --color "FF4500" --description "Priority 2" 2>/dev/null || true
gh label create "queue-3" --color "FF8C00" --description "Priority 3" 2>/dev/null || true
gh label create "queue-4" --color "FFD700" --description "Priority 4" 2>/dev/null || true
gh label create "queue-5" --color "9ACD32" --description "Priority 5" 2>/dev/null || true
```

## Вывод

```markdown
## Backlog Queue Updated

| Queue | Issue | Title | Weight | Reason |
|-------|-------|-------|--------|--------|
| 1 | #401 | Fix critical bug | 150 | critical + blocks #402 |
| 2 | #403 | Add validation | 70 | bug + old (10 days) |
| 3 | #405 | Update docs | 25 | enhancement |

### Changes Made
- #401: added `queue-1`
- #403: changed `queue-5` → `queue-2`
- #405: added `queue-3`

### Blocked Issues (not in queue)
- #410: blocked by #401 (open)
```

## Команды после анализа

```bash
# Взять первую задачу из очереди
./scripts/task-start.sh $(gh issue list --label "queue-1" --json number -q '.[0].number')

# Показать всю очередь
gh issue list --state open --json number,title,labels --jq '.[] | select(.labels | map(.name) | any(startswith("queue-"))) | "\(.labels | map(.name) | map(select(startswith("queue-")))[0]): #\(.number) \(.title)"' | sort
```

## Режим `show`

Только показать текущую очередь без изменений:

```bash
gh issue list --state open --json number,title,labels --jq '.[] | select(.labels | map(.name) | any(startswith("queue-"))) | {queue: (.labels | map(.name) | map(select(startswith("queue-")))[0]), number, title}' | jq -s 'sort_by(.queue)'
```

## Режим `reset`

Убрать все queue-* лейблы:

```bash
for issue in $(gh issue list --state open --json number -q '.[].number'); do
    gh issue edit $issue --remove-label "queue-1,queue-2,queue-3,queue-4,queue-5,queue-6,queue-7,queue-8,queue-9,queue-10" 2>/dev/null || true
done
```
