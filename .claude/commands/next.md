# Next Task

Взять следующую задачу из очереди Supervisor.

## Действие

1. Проверить что агент зарегистрирован:
```bash
if [ ! -f ~/.claude-agent-id ]; then
    echo "Сначала запусти /ag1, /ag2, /ag3, /ag4 или /ag5"
    exit 1
fi
```

2. Взять задачу из очереди:
```bash
./scripts/agent-next.sh
```

3. Если скрипт вернул номер issue:
   - Запустить `./scripts/task-start.sh <issue>`
   - Сообщить: "Взял issue #N, начинаю работу..."
   - Начать работу над issue

4. Если очередь пуста:
   - Сообщить: "Нет задач в очереди. Добавь через `./scripts/agent-add-task.sh <issue>` или label `agent-ready`"
