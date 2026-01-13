# Issue #710: Колонки transcripts используют PascalCase вместо snake_case

## Что изменено

- Создана миграция `047_transcripts_snake_case.sql` для переименования колонок:
  - `Status` → `status`
  - `Name` → `name`
  - `TranslateText` → `translate_text`
  - `TranslateStatus` → `translate_status`
  - `ConvertStatus` → `convert_status`
  - `AudioID` → `audio_id`
  - `VideoID` → `video_id`
  - `TranscribeStatus` → `transcribe_status`
  - `RenderStatus` → `render_status`
  - `LastWebhookAt` → `last_webhook_at`

- Обновлён код в:
  - `src/routes/transcripts.py` — Pydantic модель и логирование
  - `temporal/activities/transcription.py` — INSERT и SELECT запросы

- Обновлена документация в `docs/SCHEMA_REFERENCE.md`

## Test

```bash
cd decision-engine-service && python -c "from src.routes.transcripts import TranscriptStatusPayload; p = TranscriptStatusPayload(id=1, creative_id='test', convert_status='finish'); print(f'OK: {p.convert_status}')"
```
