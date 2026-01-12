# Backlog Priority Manager

Анализ и приоритизация issues через лейблы `queue-1`, `queue-2`, `queue-3`...
Плюс группировка параллельных задач через `parallel-A`, `parallel-B`...

## Использование

```
/backlog              — анализ + расставить лейблы очередности + параллельные группы
/backlog show         — только показать текущую очередь (без изменений)
/backlog parallel     — только показать параллельные группы
/backlog reset        — убрать все queue-* и parallel-* лейблы
```

## Лейблы очередности

| Лейбл | Значение |
|-------|----------|
| `queue-1` | Делать первым |
| `queue-2` | Делать вторым |
| `queue-3` | Делать третьим |
| ... | ... |

## Лейблы параллельных групп

| Лейбл | Значение |
|-------|----------|
| `parallel-A` | Группа A — можно запускать одновременно |
| `parallel-B` | Группа B — после группы A |
| `parallel-C` | Группа C — после группы B |
| `blocked` | Заблокирован другим issue |

## Процессы (для определения совместимости)

| Процесс | Ключевые слова в title/body/labels |
|---------|-----------------------------------|
| `de` | decision-engine, DE, decision |
| `ll` | learning-loop, learning, LL |
| `hf` | hypothesis-factory, hypothesis, HF |
| `vi` | video-ingestion, video, temporal |
| `kt` | keitaro, metrics, poller |
| `tg` | telegram, notification, bot |
| `db` | schema, migration, database |

## Матрица совместимости процессов

| Process | de | ll | hf | vi | kt | tg | db |
|---------|----|----|----|----|----|----|-----|
| de | - | ✅ | ❌ | ✅ | ✅ | ✅ | ❌ |
| ll | ✅ | - | ✅ | ✅ | ✅ | ✅ | ❌ |
| hf | ❌ | ✅ | - | ✅ | ✅ | ✅ | ❌ |
| vi | ✅ | ✅ | ✅ | - | ✅ | ✅ | ❌ |
| kt | ✅ | ✅ | ✅ | ✅ | - | ✅ | ❌ |
| tg | ✅ | ✅ | ✅ | ✅ | ✅ | - | ❌ |
| db | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | - |

**Правило:** `db` (миграции) всегда выполняются отдельно первыми.

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

# Лейблы параллельных групп
gh label create "parallel-A" --color "0E8A16" --description "Parallel group A - start now" 2>/dev/null || true
gh label create "parallel-B" --color "1D76DB" --description "Parallel group B - after A" 2>/dev/null || true
gh label create "parallel-C" --color "5319E7" --description "Parallel group C - after B" 2>/dev/null || true
gh label create "blocked" --color "B60205" --description "Blocked by another issue" 2>/dev/null || true
```

### 6. Определить параллельные группы

**Алгоритм:**

1. Взять issues отсортированные по приоритету (queue)
2. Для каждого определить процесс (de, ll, hf, vi, kt, tg, db)
3. Группа A: первые N issues которые совместимы по матрице
4. Группа B: следующие совместимые issues (после зависимостей группы A)
5. Blocked: issues с открытыми зависимостями

```python
# Псевдокод
groups = {'A': [], 'B': [], 'C': []}
blocked = []

for issue in sorted_by_priority:
    if has_open_dependency(issue):
        blocked.append(issue)
        continue

    process = detect_process(issue)

    # Попробовать добавить в группу A
    if is_compatible_with_group(process, groups['A']):
        groups['A'].append(issue)
    elif is_compatible_with_group(process, groups['B']):
        groups['B'].append(issue)
    else:
        groups['C'].append(issue)
```

### 7. Обновить лейблы параллельных групп

```bash
# Убрать старые parallel-* лейблы
gh issue edit {number} --remove-label "parallel-A,parallel-B,parallel-C,blocked"

# Добавить новый лейбл группы
gh issue edit {number} --add-label "parallel-{GROUP}"
```

## Вывод

```markdown
## Backlog Analysis Complete

### Priority Queue

| Queue | Issue | Title | Process | Weight | Reason |
|-------|-------|-------|---------|--------|--------|
| 1 | #401 | Fix critical bug | de | 150 | critical + blocks #402 |
| 2 | #403 | Add validation | ll | 70 | bug + old (10 days) |
| 3 | #405 | Keitaro metrics | kt | 50 | enhancement |
| 4 | #407 | Update docs | — | 25 | docs |

### Parallel Groups

🟢 **Group A** (можно запускать СЕЙЧАС):
| Issue | Title | Process |
|-------|-------|---------|
| #401 | Fix critical bug | de |
| #403 | Add validation | ll |
| #405 | Keitaro metrics | kt |

🔵 **Group B** (после Group A):
| Issue | Title | Process | Ждёт |
|-------|-------|---------|------|
| #407 | Refactor DE | de | #401 |
| #409 | Update hypothesis | hf | — |

🔴 **Blocked**:
- #410: blocked by #401 (open)
- #412: blocked by #403 (open)

### Labels Updated
- #401: `queue-1`, `parallel-A`
- #403: `queue-2`, `parallel-A`
- #405: `queue-3`, `parallel-A`
- #407: `queue-4`, `parallel-B`
- #410: `blocked`

### Recommendation
Запустить 3 агента параллельно на Group A:
- Agent 1 → #401 (de)
- Agent 2 → #403 (ll)
- Agent 3 → #405 (kt)
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

## Режим `parallel`

Показать только параллельные группы:

```bash
echo "=== Group A (start now) ==="
gh issue list --state open --label "parallel-A" --json number,title,labels --jq '.[] | "#\(.number) \(.title)"'

echo "=== Group B (after A) ==="
gh issue list --state open --label "parallel-B" --json number,title,labels --jq '.[] | "#\(.number) \(.title)"'

echo "=== Group C (after B) ==="
gh issue list --state open --label "parallel-C" --json number,title,labels --jq '.[] | "#\(.number) \(.title)"'

echo "=== Blocked ==="
gh issue list --state open --label "blocked" --json number,title,labels --jq '.[] | "#\(.number) \(.title)"'
```

## Режим `reset`

Убрать все queue-* и parallel-* лейблы:

```bash
for issue in $(gh issue list --state open --json number -q '.[].number'); do
    gh issue edit $issue --remove-label "queue-1,queue-2,queue-3,queue-4,queue-5,queue-6,queue-7,queue-8,queue-9,queue-10,parallel-A,parallel-B,parallel-C,blocked" 2>/dev/null || true
done
```
