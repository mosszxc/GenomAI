# Issue #709: Creatives without tracker_id

## Что изменено

1. **`temporal/activities/supabase.py`**
   - Добавлен параметр `tracker_id: Optional[str] = None` в `create_creative()`
   - Если передан `tracker_id`, он сохраняется в БД при создании креатива

2. **`temporal/workflows/historical_import.py`**
   - Изменена сигнатура `CreativeRegistrationWorkflow.run()`:
     - Было: `(buyer_id, video_url, target_geo, target_vertical)`
     - Стало: `(buyer_id, video_url, tracker_id, target_vertical)`
   - tracker_id теперь передаётся в `create_creative()` и включается в event

## Причина проблемы

- `CreativeRegistrationWorkflow` не принимал параметр `tracker_id`
- В `buyer_onboarding.py` передавался `campaign["campaign_id"]` как третий аргумент
- Но workflow интерпретировал его как `target_geo` (бесполезно)
- В результате tracker_id терялся

## Влияние исправления

- Новые креативы из onboarding будут иметь `tracker_id`
- Обычные креативы из Telegram (вне onboarding) продолжат работать с `tracker_id=null`
- Креативы с tracker_id будут получать метрики из Keitaro

## Test

```bash
# Проверить что параметр tracker_id принимается в create_creative
cd decision-engine-service && python3 -c "
from temporal.activities.supabase import create_creative
import inspect
sig = inspect.signature(create_creative)
params = list(sig.parameters.keys())
assert 'tracker_id' in params, f'tracker_id not found in {params}'
print('OK: tracker_id parameter exists in create_creative')
"
```
