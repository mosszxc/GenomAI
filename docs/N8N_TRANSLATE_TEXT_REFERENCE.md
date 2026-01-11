# N8N TranslateText Workflow Reference

Эталонный документ для workflow перевода транскриптов в GenomAI.

## Overview

| Параметр | Значение |
|----------|----------|
| **Workflow ID** | `fcnpPrj9sCFUqoWF` |
| **Webhook Path** | `cbe04bc1-212e-44d5-98fe-dcc21043502c` |
| **LLM Provider** | DeepSeek |
| **Целевая таблица** | `genomai.transcripts` |
| **Целевой язык** | Русский |

## Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  POST Webhook                                                       │
│  body: { id, transcript_text, ... }                                 │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────┐                                                   │
│  │ Code15       │ Split text into chunks (MAX_CHARS=800)            │
│  │ Smart Split  │ by paragraphs → sentences → hard cut              │
│  └──────┬───────┘                                                   │
│         │ [chunk1, chunk2, ...]                                     │
│         ▼                                                           │
│  ┌──────────────┐                                                   │
│  │ Loop Over    │◄────────────────────────┐                         │
│  │ Items        │                         │                         │
│  └──────┬───────┘                         │                         │
│         │                                 │                         │
│    ┌────┴────┐                            │                         │
│    │         │                            │                         │
│    ▼         ▼                            │                         │
│  done     next item                       │                         │
│    │         │                            │                         │
│    │         ▼                            │                         │
│    │  ┌──────────────┐                    │                         │
│    │  │ Basic LLM    │ ◄── DeepSeek       │                         │
│    │  │ Chain        │     Chat Model     │                         │
│    │  │ (translate)  │                    │                         │
│    │  └──────┬───────┘                    │                         │
│    │         │                            │                         │
│    │         └────────────────────────────┘                         │
│    │                                                                │
│    ▼                                                                │
│  ┌──────────────┐                                                   │
│  │ Code JS      │ Join all translated chunks                        │
│  │ (merge)      │                                                   │
│  └──────┬───────┘                                                   │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────┐                                                   │
│  │ Update row   │ TranslateText, TranslateStatus=finish             │
│  │ Supabase     │ Status=finish                                     │
│  └──────────────┘                                                   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Webhook Input

```json
{
  "body": {
    "id": "uuid|int",           // genomai.transcripts.id
    "transcript_text": "string", // текст для перевода
    "creative_id": "uuid",       // optional
    "version": 1                 // optional
  }
}
```

## Text Chunking Algorithm (Code15)

### Параметры
- `MAX_CHARS = 800` — максимальный размер чанка

### Логика разбиения
1. Разбить по абзацам (двойной перенос `\n\n`)
2. Если абзац > MAX_CHARS → разбить по предложениям (`[.!?]`)
3. Если предложение > MAX_CHARS → жёсткая нарезка по символам
4. Буферизация: склеиваем мелкие куски пока не превысим лимит

### Output формат
```json
[
  {
    "text": "chunk text",
    "partIndex": 1,
    "partTotal": 5,
    "originalId": "...",
    "creative_id": "...",
    "version": 1
  }
]
```

## LLM Translation Prompt

```
Ты — профессиональный переводчик.

Твоя задача — выполнить СТРОГО ИДЕНТИЧНЫЙ ПЕРЕВОД текста.

ОБЯЗАТЕЛЬНЫЕ ПРАВИЛА:
1. Переводи МАКСИМАЛЬНО ДОСЛОВНО, без перефразирования.
2. НЕ улучшай стиль. НЕ делай текст "красивее".
3. НЕ меняй порядок предложений.
4. НЕ сокращай и НЕ расширяй текст.
5. НЕ добавляй никаких пояснений, комментариев, заголовков.
6. Сохраняй:
   - все эмоции,
   - агрессию,
   - манипуляции,
   - риторику,
   - повторы,
   - логические акценты.
7. Числа, проценты, возраст, интервалы, даты — сохраняй ТОЧНО.
8. Если в тексте есть ошибки — ПЕРЕВОДИ С ОШИБКАМИ, не исправляй их.
9. Если предложение обрывается — ПЕРЕВОДИ ТАК ЖЕ ОБОРВАННЫМ.
10. Никакой цензуры. Никаких "смягчений".

ФОРМАТ ВЫВОДА:
- Выводи ТОЛЬКО переведённый текст.
- Никаких пояснений.
- Никаких кавычек.
- Никаких markdown-блоков.
- Никаких вступлений.

ЯЗЫК ПЕРЕВОДА: РУССКИЙ
Если между обратными апострофами ` ` нет текста — выведи строго: Ожидаю текст
```

### Ключевые принципы промпта
- **Дословность** — без перефразирования
- **Сохранение ошибок** — если оригинал с ошибками, перевод тоже
- **Без цензуры** — сохранять агрессию, манипуляции
- **Чистый output** — только текст, без markdown/комментариев

## Merge Logic (Code in JavaScript)

```javascript
const fullText = items
  .map(item => item.json?.text || '')
  .filter(t => t.trim() !== '')
  .join(' ')           // склеиваем через пробел
  .replace(/\s+/g, ' ') // убираем двойные пробелы
  .trim();
```

## Database Updates

### Success Case
```sql
UPDATE genomai.transcripts
SET
  "TranslateText" = '<merged_translation>',
  "TranslateStatus" = 'finish',
  "Status" = 'finish'
WHERE id = '<webhook.body.id>';
```

## Credentials Required

| Service | Credential Name | Type |
|---------|-----------------|------|
| DeepSeek | "Main" | API Key |
| Supabase | "Main" | API Key |

## Retry Logic

- **LLM Chain**: `retryOnFail: true`, `waitBetweenTries: 3000ms`

## Pipeline Integration

```
AudioTranscribe                    TranslateText
     │                                  │
     │ TranscribeStatus=finish          │
     │ TranslateStatus=queued ──────────┼─► Webhook trigger
     │                                  │
     ▼                                  ▼
genomai.transcripts             genomai.transcripts
  transcript_text                 TranslateText
                                  TranslateStatus=finish
                                  Status=finish
```

### Trigger Mechanism
После AudioTranscribe устанавливает `TranslateStatus=queued`, Supabase webhook
или scheduled job должен вызвать TranslateText webhook.

## Table Schema Reference

```sql
-- genomai.transcripts (relevant columns)
id                 UUID/INT PRIMARY KEY
transcript_text    TEXT      -- исходный текст (input)
"TranslateText"    TEXT      -- переведённый текст (output)
"TranslateStatus"  TEXT      -- queued, processing, finish, error
"Status"           TEXT      -- общий статус записи
creative_id        UUID      -- связь с креативом
version            INT       -- версия
```

## Error Handling

| Ситуация | Поведение |
|----------|-----------|
| Пустой текст | Code15 возвращает пустой массив, workflow завершается |
| LLM timeout | Retry через 3 сек |
| Code15 error | `continueErrorOutput` — идёт дальше |

## Performance Considerations

- **Chunk size 800** — баланс между качеством перевода и latency
- **Batch processing** — чанки обрабатываются последовательно (не параллельно)
- **DeepSeek** — быстрее и дешевле GPT для перевода

## Raw Workflow JSON

Оригинальный файл: `/Users/mosszxc/Downloads/TranslateText.json`

## Future Improvements

- [ ] Добавить error status в БД при падении
- [ ] Параллельная обработка чанков (осторожно с rate limits)
- [ ] Кэширование уже переведённых сегментов
- [ ] Language detection для выбора direction перевода
- [ ] Добавить метрики: время перевода, количество токенов
