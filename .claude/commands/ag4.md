# Agent 4

Устанавливает этот терминал как Agent 4.

## Действие

1. Записать ID в файл:
```bash
echo "agent-4" > ~/.claude-agent-id
```

2. Зарегистрировать агента в Supabase:
```bash
./scripts/agent-register.sh
```

3. Подтвердить пользователю:
```
Этот терминал теперь agent-4
```
