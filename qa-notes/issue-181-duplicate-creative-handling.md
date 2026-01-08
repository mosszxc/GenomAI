# QA Notes: Issue #181 — Duplicate Creative Handling

## Problem
При повторной отправке креатива с тем же `(video_url, tracker_id)` бот молчал. Причина: UNIQUE constraint violation → 409 Conflict → workflow падал без ответа пользователю.

## Solution
Добавлена обработка ошибки в `Zaliv Session Handler` (97cj3kRY6zzlAy0M):

```
Register Creative (onError: continueRegularOutput)
    → Check Duplicate (IF: $json.id exists)
        ├─ true → Increment Counter → [Send Creative Message, Call Transcription]
        └─ false → Send Duplicate Message
```

## Edge Cases

1. **409 Conflict** — теперь обрабатывается, пользователь получает сообщение
2. **Другие HTTP ошибки** (500, timeout) — также идут на false branch, пользователь получает сообщение о дубликате (неточно, но лучше чем молчание)
3. **Пустой ответ** — если Supabase вернёт пустой массив, также false branch

## Gotchas

- `onError: continueRegularOutput` — workflow продолжается с обычным output (не error output)
- IF нода проверяет `$json.id` — это поле возвращается только при успешном INSERT
- При 409 Supabase возвращает `{"code": "23505", "message": "..."}` — нет `id` поля

## Validation

- Execution #2703: подтвердил false branch при дубликате
- Ошибка Telegram "chat not found" — тестовый chat_id, логика верна

## Related

- Constraint: `creatives_video_url_tracker_id_key` на `(video_url, tracker_id)`
- Workflow: `Zaliv Session Handler` (97cj3kRY6zzlAy0M)
