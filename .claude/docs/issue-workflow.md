# Issue Workflow

## Начало работы
```bash
./scripts/task-start.sh <issue-number>
```
Создаёт worktree из develop, ставит label in-progress.

## Работа
1. Понять задачу: `gh issue view <N>`
2. Проверить схему БД если нужно
3. Написать код
4. Commit + push

## Завершение
```bash
./scripts/task-done.sh <issue-number>
```
Автоматически:
- Запускает локальный тест (test-local.sh)
- Запускает unit тесты (make ci)
- Проверяет qa-notes
- Создаёт PR в develop

## qa-notes (обязательно)
Создать `qa-notes/issue-XXX-*.md` с:
- Что изменено
- Как тестировать
- Edge cases
