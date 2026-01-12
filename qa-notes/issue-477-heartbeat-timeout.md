# Issue #477: Heartbeat timeout 60 сек слишком короткий для transcription

## Что изменено

- Увеличен `heartbeat_timeout` для transcribe_audio activity с 60 секунд до 5 минут
- Файл: `decision-engine-service/temporal/workflows/creative_pipeline.py:166`

## Причина

AssemblyAI может обрабатывать аудио 5-15 минут. При heartbeat_timeout=60s:
1. Activity отправляет heartbeat каждые 30 сек (POLL_INTERVAL)
2. Если AssemblyAI API тормозит 2+ минуты → heartbeat timeout
3. Temporal убивает activity → retry → exhausted retries

## Решение

`heartbeat_timeout=timedelta(minutes=5)` позволяет до 10 polling cycles (5 мин / 30 сек) без heartbeat timeout.

## Test

```bash
grep -q "heartbeat_timeout=timedelta(minutes=5)" decision-engine-service/temporal/workflows/creative_pipeline.py && echo "OK: heartbeat_timeout=5min"
```
