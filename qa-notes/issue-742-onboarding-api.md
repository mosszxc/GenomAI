# Issue #742: API Endpoints для онбоардинга

## Что изменено

### Новые файлы
- `decision-engine-service/src/routes/onboarding.py` — API endpoints для онбоардинга
- `decision-engine-service/src/routes/buyers.py` — API endpoint для информации о buyer

### Изменённые файлы
- `decision-engine-service/main.py` — добавлены роутеры onboarding и buyers

### Новые endpoints

| Endpoint | Метод | Описание |
|----------|-------|----------|
| `/api/onboarding/validate-keitaro` | POST | Валидация Keitaro credentials |
| `/api/onboarding/start` | POST | Запуск онбоардинга |
| `/api/onboarding/status` | GET | Статус и прогресс онбоардинга |
| `/api/onboarding/submit-video` | POST | Отправка видео для campaign |
| `/api/onboarding/skip-videos` | POST | Пропуск этапа видео |
| `/api/buyers/me` | GET | Информация о текущем buyer |

### Авторизация

Все endpoints требуют JWT токен в заголовке `Authorization: Bearer {token}`.
Токен получается через `POST /api/auth/telegram`.

Формат токена: `{buyer_id}:{timestamp}:{signature}`

## Test

```bash
# Проверка что endpoints доступны (должен вернуть 401 без токена)
curl -sf -o /dev/null -w "%{http_code}" localhost:10000/api/onboarding/status && echo "FAIL: should return 401" || echo "OK: auth required"
```

## Ручное тестирование

### 1. Получить токен

```bash
# Через Telegram Login Widget (требует реального Telegram auth)
curl -X POST localhost:10000/api/auth/telegram \
  -H "Content-Type: application/json" \
  -d '{"id": 123456, "first_name": "Test", "auth_date": 1234567890, "hash": "..."}'
```

### 2. Валидация Keitaro

```bash
curl -X POST localhost:10000/api/onboarding/validate-keitaro \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "keitaro_url": "https://tracker.example.com",
    "keitaro_api_key": "your-api-key"
  }'
```

### 3. Запуск онбоардинга

```bash
curl -X POST localhost:10000/api/onboarding/start \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Buyer",
    "geos": ["US", "DE"],
    "verticals": ["POT"],
    "keitaro_url": "https://tracker.example.com",
    "keitaro_api_key": "your-api-key",
    "keitaro_source": "TB"
  }'
```

### 4. Проверка статуса

```bash
curl localhost:10000/api/onboarding/status \
  -H "Authorization: Bearer {token}"
```

### 5. Отправка видео

```bash
curl -X POST localhost:10000/api/onboarding/submit-video \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "campaign_id": "12345",
    "video_url": "https://example.com/video.mp4"
  }'
```

### 6. Пропуск видео

```bash
curl -X POST localhost:10000/api/onboarding/skip-videos \
  -H "Authorization: Bearer {token}"
```

### 7. Информация о buyer

```bash
curl localhost:10000/api/buyers/me \
  -H "Authorization: Bearer {token}"
```

## Связанные задачи

- Frontend: mosszxc/cockpit#198
