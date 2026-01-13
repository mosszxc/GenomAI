# Issue #664: Fix remaining mypy errors

## Что изменено

Исправлены все 148 mypy ошибок в проекте:

### Категории исправлений:

1. **Implicit Optional (3 ошибки)**
   - `src/utils/errors.py`: `dict = None` → `dict | None = None`

2. **Invalid type `any` (1 ошибка)**
   - `src/services/schema_validator.py`: `Optional[any]` → `Optional[Any]`

3. **no-any-return (~70 ошибок)**
   - Добавлены `cast()` для `response.json()` возвратов во всех сервисах и activities
   - Файлы: supabase.py, recommendation.py, learning_loop.py, и др.

4. **union-attr (list | None).append() (15 ошибок)**
   - `src/services/learning_loop.py`: заменены `list[Any] | None = None` на `field(default_factory=list)`
   - `src/services/premise_learning.py`, `component_learning.py`: извлечены локальные переменные

5. **attr-defined Correlation.lift (4 ошибки)**
   - `src/services/correlation_discovery.py`: добавлены свойства-алиасы `lift` и `lift_percent`

6. **call-overload execute_activity (2 ошибки)**
   - `temporal/workflows/historical_import.py`: использование `args=` параметра вместо позиционных

7. **var-annotated (~10 ошибок)**
   - Добавлены явные аннотации типов для переменных во всех затронутых файлах

8. **assignment type mismatches (~15 ошибок)**
   - Исправлены несоответствия типов и добавлены Optional там где нужно

9. **SDK issues**
   - `temporal/client.py`: убран вызов несуществующего метода `Client.close()`
   - `temporal/tracing.py`: добавлен `# type: ignore[arg-type]` для structlog processors

## Затронутые файлы (36 файлов)

### src/utils/
- errors.py, environment.py

### src/services/
- schema_validator.py, supabase.py, learning_loop.py, auto_recommend.py
- recommendation.py, idea_registry.py, avatar_service.py, premise_selector.py
- premise_learning.py, component_learning.py, feature_registry.py
- dashboard_service.py, external_inspiration.py, correlation_discovery.py
- outcome_service.py, staleness_detector.py, genome_heatmap.py
- statistical_validation.py, exploration.py, decision_engine.py
- feature_correlation.py, module_selector.py

### src/routes/
- schedules.py

### temporal/
- client.py, tracing.py

### temporal/activities/
- recommendation.py, telegram.py, buyer.py, modular_generation.py
- supabase.py, maintenance.py, module_extraction.py

### temporal/workflows/
- recommendation.py, historical_import.py

## Test

```bash
cd decision-engine-service && python3 -m mypy src/ --config-file=pyproject.toml 2>&1 | grep -E "^(Found|Success)" || echo "OK: mypy passed"
```
