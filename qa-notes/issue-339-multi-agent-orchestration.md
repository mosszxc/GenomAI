# Issue #339: Multi-Agent Orchestration Phase 1

## Problem
Несколько Claude Code агентов работают параллельно в Cursor и сталкиваются с:
- Merge conflicts (редактируют одни файлы)
- Deploy queue overflow (несколько PR мержатся одновременно)
- Дублирование работы (берут один и тот же issue)

## Solution
Реализована Phase 1 — lock-файлы для координации задач:

### Изменённые файлы
| Файл | Изменение |
|------|-----------|
| `scripts/task-start.sh` | Создаёт lock при старте задачи |
| `scripts/task-done.sh` | Удаляет lock при завершении |
| `CLAUDE.md` | Добавлена секция Multi-Agent Task Coordination |
| `.agents/STATUS.md` | Shared status board |
| `.agents/.gitignore` | Игнорирует locks/ директорию |

### Механизм работы
1. `task-start.sh` создаёт `.agents/locks/issue-{N}.lock` с JSON metadata
2. Если lock существует — показывает кто занял issue и блокирует
3. `task-done.sh` удаляет lock после cleanup worktree

### Lock файл формат
```json
{
  "agent": "hostname-12345",
  "issue": 339,
  "title": "Multi-Agent Orchestration Phase 1",
  "started_at": "2025-01-11T10:00:00Z"
}
```

## Test Commands
```bash
# Показать активных агентов
./scripts/task-start.sh

# Создать тестовый lock
mkdir -p .agents/locks
echo '{"agent": "test-agent", "issue": 100, "started_at": "2025-01-11T10:00:00Z"}' > .agents/locks/issue-100.lock

# Попробовать взять занятый issue
./scripts/task-start.sh 100
# Ожидается: блокировка с информацией об агенте

# Удалить lock
rm .agents/locks/issue-100.lock
```

## Edge Cases
- **Lock file race condition**: Используется mv для atomic write
- **Stale locks**: Если агент упал — lock остаётся, требуется ручное удаление
- **Force claim**: `rm .agents/locks/issue-N.lock` позволяет перехватить задачу

## Future (Phase 2)
- Supabase таблица `agent_tasks` для централизованной координации
- Heartbeat механизм для automatic orphan detection
- Agent registration при старте сессии
