# Issue #477: Heartbeat timeout 60 сек слишком короткий для transcription

## Что изменено

- Увеличен `heartbeat_timeout` с 60 секунд до 5 минут в `creative_pipeline.py:166`
- Activity уже отправляет heartbeat каждые 30 секунд при polling AssemblyAI
- Увеличенный timeout даёт запас на сетевые задержки и медленные ответы API

## Почему 5 минут

- AssemblyAI может обрабатывать 2-10 минут
- Poll interval = 30 сек, HTTP timeout = 30 сек
- При задержках heartbeat мог не успевать за 60 сек
- 5 минут даёт достаточный запас без риска зависания

## Test

```bash
grep -q "heartbeat_timeout=timedelta(minutes=5)" .worktrees/issue-477-arch-high-heartbeat-timeout-60-сек-слишк/decision-engine-service/temporal/workflows/creative_pipeline.py && echo "OK: heartbeat_timeout=5min"
```
