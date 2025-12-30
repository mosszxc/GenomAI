# Issue #180: Zaliv session shows 0 creatives at /done

## Problem
При завершении сессии заливки командой `/done` бот показывал "Зарегистрировано креативов: 0", хотя креативы регистрировались успешно.

## Root Cause
Expression в ноде `Send Done Message` обращался к `json[0]` вместо `json`:

```javascript
// БАГ:
$('Get Session Stats').first().json[0]?.zaliv_session_count || 0
// json[0] на объекте = undefined → всегда 0

// ИСПРАВЛЕНО:
$('Get Session Stats').first().json.zaliv_session_count || 0
```

## Why It Happened
HTTP Request node в n8n разворачивает массив от API в отдельные items:
- Supabase REST API возвращает: `[{zaliv_session_count: 1, ...}]`
- n8n превращает это в: item с `json: {zaliv_session_count: 1, ...}`

Автор expression думал что `json` это массив, но это уже объект.

## Gotchas
1. `$('Node').first().json` — это уже объект, не массив
2. Supabase REST API возвращает массив, но n8n разворачивает его
3. `json[0]` на объекте возвращает `undefined`, не ошибку

## How to Debug
1. Смотреть execution data в n8n UI
2. Проверять `$('Node').first().json` структуру
3. Execution ID 2637 показала что данные правильные, но expression неверный

## Affected
- Workflow: `Zaliv Session Handler` (97cj3kRY6zzlAy0M)
- Node: `Send Done Message`

## Prevention
- Всегда проверять структуру output node перед написанием expression
- Использовать n8n expression editor для preview
