# Issue #623: task-done.sh fallback to current branch

## Что изменено

- Добавлен fallback в `task-done.sh`: если worktree не найден, скрипт проверяет текущую ветку
- Если имя текущей ветки содержит номер issue - используется текущая директория
- Улучшено сообщение об ошибке с подсказками

## Файлы

- `scripts/task-done.sh:61-79`

## Test

```bash
cd /Users/mosszxc/Documents/Проэкты/GenomAI && bash -n scripts/task-done.sh && echo "OK: syntax valid"
```
