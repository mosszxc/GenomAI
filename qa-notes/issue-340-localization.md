# QA Notes: Issue #340 - Локализация Telegram сообщений

## Scope
Перевод всех пользовательских сообщений Telegram бота на русский язык.
Команды (`/help`, `/stats`, etc.) остаются на английском.

## Изменённые файлы (8)

| Файл | Изменения |
|------|-----------|
| `src/routes/telegram.py` | 40+ сообщений: help, errors, callbacks, registration |
| `src/services/genome_heatmap.py` | Матрица компонентов, сегментация |
| `src/services/confidence.py` | Доверительные интервалы |
| `src/services/drift_detection.py` | Обнаружение дрифта, рекомендации |
| `src/services/what_if_simulator.py` | Результаты симуляции |
| `src/services/correlation_discovery.py` | Найденные корреляции |
| `src/services/auto_recommend.py` | Лучшая ставка дня |
| `temporal/activities/telegram.py` | Доставка гипотез |

## Ключевые переводы

| До | После |
|----|-------|
| "You already have an active registration..." | "У вас уже есть активная регистрация..." |
| "Stats temporarily unavailable" | "Статистика временно недоступна" |
| "Component Performance Matrix" | "Матрица компонентов" |
| "Win Rate Trends" | "Тренды конверсии" |
| "Performance Drift Detected" | "Обнаружен дрифт" |
| "Today's Best Bet" | "Лучшая ставка дня" |
| "Discovered Correlations" | "Найденные корреляции" |
| "Simulation Result" | "Результат симуляции" |
| "New Hypothesis Generated" | "Новая гипотеза" |

## Тестирование

### Syntax Check
- [x] Pre-commit hooks прошли (ruff lint, ruff format, critical tests)
- [x] Unit tests прошли (pre-push hook)

### Функциональное тестирование
Локализация не меняет логику, только текстовые строки в HTML-сообщениях.
Проверка функциональности будет выполнена после деплоя на Render.

**Команды для тестирования:**
- `/start` - сообщение регистрации
- `/help` - список команд на русском
- `/stats` - статистика (уже была частично на русском)
- `/genome` - матрица компонентов
- `/confidence` - доверительные интервалы
- `/drift` - обнаружение дрифта
- `/correlations` - корреляции
- `/recommend` - рекомендации

## Известные ограничения

1. `temporal/workflows/buyer_onboarding.py` - не изменён, уже на русском
2. Callback кнопки Approve/Reject переведены (Одобрено/Отклонено)
3. Форматирование сохранено (HTML parse_mode)

## Риски

- **Низкий**: Изменения только в строковых литералах
- HTML-теги (`<b>`, `<i>`, `<code>`) сохранены
- Unicode (кириллица) поддерживается Telegram API
