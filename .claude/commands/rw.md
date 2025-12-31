# Ralph Wiggum Loop (rw)

Ralph Wiggum loop ограниченный одним процессом.

## Формат

```
/rw {процесс}
```

## Действие

1. Запусти bash скрипт:

```bash
/Users/mosszxc/.claude/plugins/cache/claude-plugins-official/ralph-wiggum/6d3752c000e2/scripts/setup-ralph-loop.sh $ARGUMENTS
```

2. Работай **СТРОГО** в рамках указанного процесса.

## Процессы

| Процесс | Workflows | Таблицы |
|---------|-----------|---------|
| загрузка креатива | Spy Creative Registration | spy_creatives, decomposed_creatives |
| learning loop | Learning Loop | learnings, metrics_daily |
| hypothesis factory | Hypothesis Factory | hypotheses, ideas |
| decision engine | Decision Engine Webhook | decisions, ideas |
| video ingestion | Video Ingestion, Video Transcription | videos, transcripts |
| keitaro poller | Keitaro Metrics Poller | metrics_daily, creatives |

## Правила

1. **НЕ ТРОГАТЬ** workflows/таблицы/код вне указанного процесса
2. Если задача требует изменений в другом процессе — СТОП, сообщи пользователю
3. После завершения — `/valid {process}`

## Примеры

```
/rw загрузка креатива
/rw learning loop
/rw decision engine
```
