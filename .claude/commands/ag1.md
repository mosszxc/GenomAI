# Agent 1

Устанавливает этот терминал как Agent 1.

## Действие

1. Записать ID в файл:
```bash
echo "agent-1" > ~/.claude-agent-id
```

2. Зарегистрировать агента в Supabase:
```bash
./scripts/agent-register.sh
```

3. Подтвердить пользователю:
```
Этот терминал теперь agent-1
```
