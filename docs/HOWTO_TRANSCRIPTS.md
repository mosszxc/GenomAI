# How to: Транскрибация видео

Краткая инструкция для запуска транскрибации через n8n pipeline.

## 1. Создать запись

```bash
curl -X POST "$SUPABASE_URL/rest/v1/transcripts" \
  -H "apikey: $SUPABASE_KEY" \
  -H "Content-Profile: genomai" \
  -H "Content-Type: application/json" \
  -d '{
    "Name": "My Video",
    "VideoID": "GOOGLE_DRIVE_FILE_ID",
    "Status": "queued",
    "ConvertStatus": "queued",
    "version": 1
  }'
```

**VideoID** извлечь из URL:
```
https://drive.google.com/file/d/1pCTMewFGP-ypWfx-DAjLXSiYUo5f0Iex/view
                                ▲
VideoID: 1pCTMewFGP-ypWfx-DAjLXSiYUo5f0Iex
```

## 2. Мониторить статус

```bash
curl "$SUPABASE_URL/rest/v1/transcripts?id=eq.{ID}&select=Status,ConvertStatus,TranscribeStatus,TranslateStatus" \
  -H "apikey: $SUPABASE_KEY" \
  -H "Accept-Profile: genomai"
```

## 3. Pipeline статусы

| Этап | Статус | Что делает |
|------|--------|------------|
| ConvertStatus | queued → processing → finish | MP4 → MP3 |
| TranscribeStatus | queued → processing → finish | AssemblyAI |
| TranslateStatus | queued → processing → finish | ES → RU |
| Status | queued → processing → finish | Общий |

## 4. Результат

- `transcript_text` — оригинал (испанский)
- `TranslateText` — перевод (русский)

## Подробнее

См. `docs/TRANSCRIPT_WEBHOOK.md`
