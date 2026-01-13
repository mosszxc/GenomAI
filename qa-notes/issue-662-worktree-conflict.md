# Issue #662 — Remove --delete-branch to avoid worktree conflicts

## Что изменено

- Убран флаг `--delete-branch` из `gh pr merge` в `scripts/task-done.sh`
- GitHub автоматически удаляет remote ветки после merge
- Локальные ветки можно чистить: `git fetch --prune`

## Причина

При использовании git worktrees, `--delete-branch` вызывает ошибку:
```
fatal: 'develop' is already checked out at '/path/to/worktree'
```

## Файлы

- `scripts/task-done.sh` (строки 296-302)

## Test

```bash
grep -q "delete-branch" scripts/task-done.sh && echo "FAIL: --delete-branch still present" && exit 1 || echo "OK: --delete-branch removed"
```
