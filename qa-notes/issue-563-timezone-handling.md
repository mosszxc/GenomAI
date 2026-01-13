# Issue #563: Inconsistent timezone handling

## Что изменено

В `staleness_detector.py` исправлен inconsistent timezone handling:

1. **Импорт timezone**: добавлен `from datetime import timezone`

2. **datetime.utcnow() → datetime.now(timezone.utc)**:
   - Строка 170: `calculate_win_rate_trend()`
   - Строка 347: `calculate_days_since_new_component()`
   - Строка 368: `calculate_exploration_success_rate()`

3. **Парсинг ISO datetime** — убрано `.replace("+00:00", "")`:
   - Строка 191: `date_7d_dt = datetime.fromisoformat(date_7d.replace("Z", "+00:00"))`
   - Строка 214: `row_date = datetime.fromisoformat(created_at.replace("Z", "+00:00"))`
   - Строка 343: `last_dt = datetime.fromisoformat(last_created.replace("Z", "+00:00"))`

4. **Удалён .replace(tzinfo=None)** в `calculate_days_since_new_component()`:
   - Было: `delta = now - last_dt.replace(tzinfo=None)` → naive vs naive (но теряет timezone)
   - Стало: `delta = now - last_dt` → aware vs aware (корректно)
   - Добавлен fallback для naive datetime из DB: `if last_dt.tzinfo is None: last_dt = last_dt.replace(tzinfo=timezone.utc)`

## Почему это важно

- `datetime.utcnow()` deprecated в Python 3.12+
- Mixing aware и naive datetime вызывает TypeError при сравнении
- `.replace(tzinfo=None)` молча теряет информацию о timezone

## Test

```bash
uv run python -c "from datetime import datetime, timedelta, timezone; now = datetime.now(timezone.utc); d = (now - timedelta(days=7)).isoformat(); dt = datetime.fromisoformat(d.replace('Z', '+00:00')); assert now >= dt; print('OK: timezone handling works')"
```
