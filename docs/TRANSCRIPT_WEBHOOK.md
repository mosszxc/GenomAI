# Transcript Webhook & Pipeline

Полный флоу транскрибации видео: от Google Drive до переведённого текста.

**Last tested:** 2026-01-12

---

## Архитектура

```
┌──────────────┐    INSERT     ┌──────────────┐    pg_cron     ┌──────────────┐
│   Supabase   │ ◄──────────── │  User/API    │                │   n8n        │
│  transcripts │               │              │                │  Workflows   │
│  (queued)    │ ─────────────────────────────────────────────►│              │
└──────────────┘                                               └──────────────┘
       │                                                              │
       │  UPDATE (status changes)                                     │
       ▼                                                              ▼
┌──────────────┐    pg_net     ┌──────────────┐              ┌──────────────┐
│  pg_cron     │ ─────────────►│  n8n Render  │ ────────────►│ Render API   │
│  worker      │   webhook     │  workflow    │  HTTP POST   │ /webhook/    │
└──────────────┘               └──────────────┘              │ transcript-  │
                                                             │ status       │
                                                             └──────────────┘
```

**Этапы обработки:**
```
ConvertStatus:   queued → processing → finish     (MP4 → MP3, Google Drive)
TranscribeStatus: queued → sent → finish          (AssemblyAI)
TranslateStatus:  queued → processing → finish    (перевод на русский)
Status:           queued → processing → finish    (общий статус)
```

---

## Как запустить транскрибацию

> **ВАЖНО: Заполнять ТОЛЬКО эти поля, остальные НЕ ТРОГАТЬ!**
>
> - `Name` — заполнить
> - `VideoID` — заполнить
> - `Status` — поставить `queued`
> - `ConvertStatus` — поставить `queued`
> - `creative_id` — заполнить (UUID креатива)
>
> **НЕ трогать другие записи! НЕ ставить статусы в существующих записях!**

### Вариант 1: Через SQL (напрямую)

```sql
-- 1. (Опционально) Создать креатив
INSERT INTO genomai.creatives (video_url, source_type, status)
VALUES ('https://drive.google.com/file/d/VIDEO_FILE_ID/view', 'user', 'pending')
RETURNING id;

-- 2. Создать НОВУЮ запись в transcripts (ТОЛЬКО эти поля!)
INSERT INTO genomai.transcripts (
  creative_id,      -- UUID креатива (ОБЯЗАТЕЛЬНО)
  "Name",           -- Любое имя (ОБЯЗАТЕЛЬНО)
  "VideoID",        -- Google Drive file ID (ОБЯЗАТЕЛЬНО)
  "Status",         -- 'queued' (ОБЯЗАТЕЛЬНО)
  "ConvertStatus",  -- 'queued' (ОБЯЗАТЕЛЬНО)
  version
) VALUES (
  'uuid-from-step-1',
  'My Video Name',
  '1_dYfD70ik8vAACQCLdJR3nVUR3vB9hQM',  -- извлечь из URL
  'queued',
  'queued',
  1
);
-- НЕ ДЕЛАТЬ UPDATE на существующие записи!
```

### Вариант 2: Через PostgREST API

```bash
# Создать НОВУЮ запись (ТОЛЬКО эти поля!)
curl -X POST "https://ftrerelppsnbdcmtcwya.supabase.co/rest/v1/transcripts" \
  -H "apikey: $SUPABASE_KEY" \
  -H "Authorization: Bearer $SUPABASE_KEY" \
  -H "Content-Type: application/json" \
  -H "Content-Profile: genomai" \
  -d '{
    "creative_id": "uuid-креатива",
    "Name": "My Video",
    "VideoID": "GOOGLE_DRIVE_FILE_ID",
    "Status": "queued",
    "ConvertStatus": "queued",
    "version": 1
  }'
# НЕ использовать PATCH/UPDATE!
```

### Извлечение VideoID из URL

```
URL: https://drive.google.com/file/d/1_dYfD70ik8vAACQCLdJR3nVUR3vB9hQM/view
                                     ▲
                                     │
VideoID: 1_dYfD70ik8vAACQCLdJR3nVUR3vB9hQM
```

---

## Схема таблицы transcripts

| Колонка | Тип | Описание |
|---------|-----|----------|
| `id` | bigint | PK, auto-increment |
| `creative_id` | uuid | FK → creatives.id (nullable) |
| `Name` | text | Имя для идентификации |
| `VideoID` | text | Google Drive file ID |
| `AudioID` | text | ID конвертированного MP3 (заполняется автоматически) |
| `ConvertStatus` | text | queued → processing → finish |
| `TranscribeStatus` | text | queued → sent → finish/error |
| `TranslateStatus` | text | queued → processing → finish |
| `Status` | text | Общий статус: queued → processing → finish |
| `transcript_text` | text | Оригинальный транскрипт (AssemblyAI) |
| `TranslateText` | text | Переведённый текст (русский) |
| `RenderStatus` | text | Статус отправки в Render API |
| `version` | int | Версия транскрипта |
| `created_at` | timestamp | Время создания |

---

## n8n Workflows

### 1. pg_cron Worker (в Supabase)
- Выбирает записи с `ConvertStatus = 'queued'`
- Вызывает n8n webhooks для обработки

### 2. n8n Render Workflow
- **ID:** `nDWwqaF58tPdJ2TZ`
- **Webhook:** `https://kazamaqwe.app.n8n.cloud/webhook/Render`
- **Функция:** Получает готовые транскрипты и отправляет в Render API

```
Webhook → Split Out → Update RenderStatus=processing
                   → Loop → Edit Fields → HTTP Request (Render API)
                         → Update RenderStatus=finish
```

---

## Render API Endpoint

### POST /webhook/transcript-status

```
POST https://genomai.onrender.com/webhook/transcript-status
Content-Type: application/json
```

**Payload:**

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
