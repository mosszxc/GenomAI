# Issue #724: Revert transcripts columns to PascalCase

## Что изменено

- Создана миграция `048_transcripts_revert_to_pascal_case.sql` — откат колонок к PascalCase
- Обновлён `transcription.py` — использует PascalCase имена колонок

## Причина

Миграция #710 переименовала колонки в snake_case, но:
- pg_cron worker использует PascalCase (`ConvertStatus = 'queued'`)
- Trigger function `notify_transcript_status()` использует PascalCase
- n8n Workflows используют PascalCase

Вместо обновления всех зависимых компонентов — откат колонок.

## Изменённые файлы

- `infrastructure/migrations/048_transcripts_revert_to_pascal_case.sql`
- `decision-engine-service/temporal/activities/transcription.py`

## Test

```bash
echo "Migration file exists" && test -f infrastructure/migrations/048_transcripts_revert_to_pascal_case.sql && echo "OK"
```
