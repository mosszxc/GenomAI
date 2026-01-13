# Agent Auto

Запуск автономного агента для решения bug issues.

## Использование

```bash
# Если аргумент - число, это количество задач
ARGS="$ARGUMENTS"
if [[ "$ARGS" =~ ^[0-9]+$ ]]; then
    ./scripts/agent-auto.sh --max-tasks "$ARGS"
else
    ./scripts/agent-auto.sh $ARGS
fi
```

## Примеры

- `/agent` — бесконечный режим
- `/agent 1` — только 1 issue
- `/agent 5` — 5 issues
- `/agent --dry-run` — посмотреть что выберет
- `/agent --skip-tests` — без запуска сервера
