# Issue #675: Progress Notifications During Creative Processing

## Что изменено

- Добавлена activity `send_status_notification` в `telegram.py`
  - Non-blocking: возвращает `success=False` вместо исключения
  - Короткий timeout (10s) для уведомлений

- Добавлены вызовы уведомлений в `CreativePipelineWorkflow`:
  - `✅ Креатив принят! Начинаю анализ...` (после загрузки креатива)
  - `🔬 Этап 1/3: Извлечение компонентов...` (перед декомпозицией)
  - `📊 Этап 2/3: Генерация гипотез...` (перед генерацией)
  - `✨ Этап 3/3: Готово! Создано N гипотез.` (после генерации)

- Зарегистрирована activity в `worker.py` и `activities/__init__.py`

## Детали реализации

- chat_id получается в начале workflow (если есть buyer_id)
- Используется helper `notify_progress()` с try/except - никогда не блокирует workflow
- RetryPolicy с maximum_attempts=1 - не пытаемся повторить уведомления

## Test

```bash
cd decision-engine-service && python3 -c "
from temporal.activities.telegram import send_status_notification
from temporalio import activity
import inspect

# Проверяем что activity определена корректно
assert hasattr(send_status_notification, '__temporal_activity_definition')
sig = inspect.signature(send_status_notification)
params = list(sig.parameters.keys())
assert params == ['chat_id', 'stage', 'message'], f'Expected params: {params}'
print('Activity send_status_notification: OK')

# Проверяем импорт в workflow
from temporal.workflows.creative_pipeline import CreativePipelineWorkflow
import ast
with open('temporal/workflows/creative_pipeline.py') as f:
    tree = ast.parse(f.read())
    source = ast.unparse(tree)
    assert 'send_status_notification' in source
    assert 'notify_progress' in source
    assert 'Этап 1/3' in source
    assert 'Этап 2/3' in source
    assert 'Этап 3/3' in source
print('Workflow progress notifications: OK')
print('ALL CHECKS PASSED')
"
```
