# Testing Rules

## Локальный тест (автоматически)

`task-done.sh` автоматически запускает `test-local.sh`:
1. Проверяет что `make up` запущен
2. Определяет тип изменений (workflow/API/migration/telegram)
3. Запускает соответствующий тест

## Перед началом работы
```bash
make up   # Запустить локальную среду
```

## Типы тестов

| Изменение | Тест |
|-----------|------|
| Workflow | curl к API + проверка |
| API endpoint | curl localhost:PORT/endpoint |
| Migration | SQL SELECT |
| Telegram | curl webhook |

## qa-notes

Создать `qa-notes/issue-XXX-*.md`:

```markdown
## Что изменено
- ...

## Тест
```bash
curl localhost:10000/endpoint
```

## Результат
HTTP 200, данные корректны
```
