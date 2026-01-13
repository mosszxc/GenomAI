# Issue #603: Telegram Dashboard UI

## Что изменено

- Добавлен новый сервис `src/services/meta_dashboard.py` для генерации Meta Dashboard
- Добавлена команда `/meta` в Telegram для получения дашборда меты
- Команда поддерживает фильтрацию по гео: `/meta US`, `/meta EU`

## Формат дашборда

```
META DASHBOARD — DE / Week 3

🔥 HOT:
├── Hook: "confession" → 47%
└── Angle: "curiosity" → 42%

❄️ COLD:
└── Angle: "fear" → fatigue HIGH

🕳️ GAPS:
└── Source: "new_tech" → 3 tests
```

## Логика категоризации

- **HOT**: win_rate >= 30%, samples >= 5
- **COLD**: usage_count >= 3 за 7 дней (fatigued)
- **GAPS**: samples < 5 (недостаточно тестов)

## Файлы

- `decision-engine-service/src/services/meta_dashboard.py` - новый сервис
- `decision-engine-service/src/routes/telegram.py` - handler и роутинг

## Test

```bash
curl -sf localhost:10000/health && echo "OK: service running"
```
