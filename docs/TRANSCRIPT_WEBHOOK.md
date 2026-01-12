# Transcript Status Webhook

Вебхук для получения уведомлений об изменении статуса обработки транскриптов.

## Обзор

Supabase отправляет HTTP POST запрос на Render сервер при изменении статусов в таблице `genomai.transcripts`:
- `ConvertStatus` (MP4 → MP3)
- `TranscribeStatus` (MP3 → текст)
- `TranslateStatus` (текст → перевод)

```
┌─────────────────┐     pg_net      ┌─────────────────────┐
│    Supabase     │ ──────────────► │   Render Service    │
│  transcripts    │   HTTP POST     │  /webhook/          │
│  table UPDATE   │                 │  transcript-status  │
└─────────────────┘                 └─────────────────────┘
```

## Endpoint

```
POST https://genomai.onrender.com/webhook/transcript-status
Content-Type: application/json
```

## Payload

```json
{
  "id": 123,
  "creative_id": "uuid-string",
  "ConvertStatus": "finish",
  "TranscribeStatus": "processing",
  "TranslateStatus": "queued",
  "changed_at": "2024-01-15T10:30:00Z"
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| id | int | ID записи в transcripts |
| creative_id | uuid | ID креатива |
| ConvertStatus | string | queued → processing → finish |
| TranscribeStatus | string | queued → processing → finish/error |
| TranslateStatus | string | queued → processing → finish |
| changed_at | timestamp | Время изменения |

## Response

```json
{
  "ok": true,
  "received": 123
}
```

## Supabase Setup

### 1. Создать функцию триггера

```sql
CREATE OR REPLACE FUNCTION genomai.notify_transcript_status()
RETURNS TRIGGER AS $$
BEGIN
  -- Отправляем только при изменении статусов
  IF (OLD.ConvertStatus IS DISTINCT FROM NEW.ConvertStatus) OR
     (OLD.TranscribeStatus IS DISTINCT FROM NEW.TranscribeStatus) OR
     (OLD.TranslateStatus IS DISTINCT FROM NEW.TranslateStatus) THEN

    PERFORM net.http_post(
      url := 'https://genomai.onrender.com/webhook/transcript-status',
      headers := '{"Content-Type": "application/json"}'::jsonb,
      body := jsonb_build_object(
        'id', NEW.id,
        'creative_id', NEW.creative_id,
        'ConvertStatus', NEW.ConvertStatus,
        'TranscribeStatus', NEW.TranscribeStatus,
        'TranslateStatus', NEW.TranslateStatus,
        'changed_at', now()
      )
    );
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

### 2. Создать триггер

```sql
DROP TRIGGER IF EXISTS transcript_status_webhook ON genomai.transcripts;

CREATE TRIGGER transcript_status_webhook
  AFTER UPDATE ON genomai.transcripts
  FOR EACH ROW
  EXECUTE FUNCTION genomai.notify_transcript_status();
```

### 3. Проверить pg_net extension

```sql
-- Должен быть включён
SELECT * FROM pg_extension WHERE extname = 'pg_net';

-- Если нет - включить в Supabase Dashboard:
-- Database → Extensions → pg_net → Enable
```

## Тестирование

### Ручной тест через SQL

```sql
-- Обновить статус
UPDATE genomai.transcripts
SET "ConvertStatus" = 'processing'
WHERE id = 123;

-- Проверить очередь pg_net
SELECT * FROM net._http_response ORDER BY created DESC LIMIT 5;
```

### Проверка логов Render

```bash
# В Render Dashboard → Service → Logs
# Искать: "Transcript status update: id=..."
```

## Статусы обработки

### Convert (MP4 → MP3)
```
queued → processing → finish
```

### Transcribe (MP3 → текст)
```
queued → processing → finish
                   → error (если файл пустой)
```

### Translate (текст → перевод)
```
queued → processing → finish
```

## Связанные компоненты

- **n8n Convert webhook**: `https://aideportment.nl.tuna.am/webhook/MP3MP4`
- **n8n Transcribe webhook**: `https://kazamaqwe.app.n8n.cloud/webhook/7c271222-...`
- **n8n Translate webhook**: `https://kazamaqwe.app.n8n.cloud/webhook/cbe04bc1-...`
- **Temporal activity**: `temporal/activities/transcription.py`

## Файлы

- `decision-engine-service/src/routes/transcripts.py` — endpoint
- `decision-engine-service/main.py` — router registration
