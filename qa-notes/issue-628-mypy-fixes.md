# Issue #628: fix(types): исправить mypy ошибки

## Что изменено

### pyproject.toml
- Добавлены mypy overrides для внешних библиотек без type stubs:
  - temporalio, structlog, openai, supabase, assemblyai, scipy, pyrogram
- Установлен `warn_unused_ignores = false` для совместимости

### Исправления типов
- Исправлены `list[str] = None` → `list[str] | None = None` в dataclass полях
- Исправлены `str = None` → `str | None = None` для опциональных переменных
- Добавлены явные аннотации `dict[str, Any]` для словарей с разными типами значений
- Исправлены конвертации `str | int` → `str` через явный `str()` вызов
- Удалены дублирующиеся поля в dataclasses
- Удалены несуществующие параметры в вызовах функций

### Файлы
- `temporal/workflows/maintenance.py` - удалён дубликат `stuck_transcription_timeout_minutes`
- `temporal/schedules.py` - удалён `buyer_state_timeout_hours`
- `temporal/workflows/creative_pipeline.py` - исправлены типы str | None
- `temporal/workflows/keitaro_polling.py` - исправлен тип errors
- `temporal/workflows/learning_loop.py` - исправлен тип errors
- `temporal/workflows/buyer_onboarding.py` - str() для telegram_id
- `src/services/learning_loop.py` - list[Any] | None для полей
- `src/services/external_inspiration.py` - dict[str, Any] для payload
- `src/routes/telegram.py` - dict[str, Any] для payload
- `temporal/worker.py` - type: ignore для lambda
- `temporal/activities/feature_monitoring.py` - аннотации для errors, drift_results

## Test

```bash
uv run mypy . 2>&1 | grep "Found.*errors" | head -1
```

Ожидаемый результат: ~142 ошибки (снижение с ~200+)
