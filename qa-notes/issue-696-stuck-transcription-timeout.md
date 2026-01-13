# Issue #696: Add stuck_transcription_timeout_minutes to MaintenanceInput

## Что изменено
- Добавлено поле `stuck_transcription_timeout_minutes: int = 30` в dataclass `MaintenanceInput`
- Файл: `decision-engine-service/temporal/workflows/maintenance.py`

## Причина
MaintenanceWorkflow падал с ошибкой:
```
'MaintenanceInput' object has no attribute 'stuck_transcription_timeout_minutes'
```

Поле использовалось в workflow (строки 199, 371), но не было объявлено в dataclass.

## Test
```bash
cd decision-engine-service && python -c "from temporal.workflows.maintenance import MaintenanceInput; m = MaintenanceInput(); print(f'stuck_transcription_timeout_minutes={m.stuck_transcription_timeout_minutes}')" && echo "OK: attribute exists"
```
