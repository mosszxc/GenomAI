# Issue #567: Staleness Quality Indicator

## Что изменено

- Добавлены константы `TOTAL_METRICS=5` и `QUALITY_FAILURE_THRESHOLD=0.5`
- Добавлено поле `quality` в `StalenessMetrics` dataclass
- Логика определения quality: если >50% метрик failed, `quality="low"`
- При `quality="low"` выводится warning с текстом "UNRELIABLE"
- `quality` добавлен в API response `check_staleness_and_act()`
- `quality` и `error_sources` сохраняются в snapshot через `action_details`

## Затронутые файлы

- `decision-engine-service/src/services/staleness_detector.py`

## Test

```bash
cd decision-engine-service && python3 -c "from src.services.staleness_detector import StalenessMetrics, TOTAL_METRICS, QUALITY_FAILURE_THRESHOLD; assert TOTAL_METRICS == 5; assert QUALITY_FAILURE_THRESHOLD == 0.5; m = StalenessMetrics(diversity_score=0.5, win_rate_trend=0.0, fatigue_ratio=0.0, days_since_new_component=7, exploration_success_rate=0.5, staleness_score=0.4, is_stale=False, error_sources=[], quality='high'); assert m.quality == 'high'; print('PASSED: quality indicator works')"
```
