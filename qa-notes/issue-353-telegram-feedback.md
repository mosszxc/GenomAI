# QA Notes: Issue #353 - Telegram /feedback команда для баеров

## Summary
Добавлена команда `/feedback` в Telegram бот для баеров. Система автоматически создаёт GitHub issue с label `buyer-feedback`.

## Changes
| File | Change |
|------|--------|
| `src/services/github_issue.py` | Новый сервис GitHub API |
| `src/routes/telegram.py` | Добавлена команда `/feedback` |
| `temporal/config.py` | Добавлен `GITHUB_TOKEN` |

## Test Results

### E2E Test: /feedback command
```bash
curl -X POST "https://genomai.onrender.com/webhook/telegram" \
  -H "Content-Type: application/json" \
  -d '{
    "update_id": 999999999,
    "message": {
      "message_id": 12345,
      "chat": {"id": 291678304},
      "from": {"id": 291678304},
      "text": "/feedback Тестовый фидбек от баера"
    }
  }'
```

**Result:**
- HTTP 200 OK
- GitHub issue #356 создан с label `buyer-feedback`
- Title: `[FEEDBACK] Тестовый фидбек от баера...`

## UX Flow
```
Баер: /feedback текст проблемы
Бот:  ✅ Заявка #XXX принята! Спасибо за обратную связь.
```

## Configuration
- `GITHUB_TOKEN` добавлен в Render env variables
- Token scope: `repo` (Issues: Read and write)

## Verification
- [x] Unit tests pass
- [x] Webhook returns 200 OK
- [x] GitHub issue created with correct label
- [x] Deploy successful (status: live)
