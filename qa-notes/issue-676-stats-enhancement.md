# Issue #676 - /stats enhancement

## Что изменено

- Древовидный формат отображения статистики
- Рекомендации на основе лучшего компонента из выигрышных креативов
- ROI с контекстом (показывает spend/revenue)

## Новый формат сообщения

```
📊 Твоя статистика

Креативов: 15
├─ ✅ Побед: 5 (33%)
├─ ❌ Поражений: 3
└─ ⏳ Тестируется: 7

💡 Совет: Твой лучший компонент — «fear».
   Используй его чаще для повышения win rate.

ROI: +45.2% ($1815 / $1250)
```

## Файлы

- `decision-engine-service/src/routes/telegram.py:620-666` - `_get_best_component()` helper
- `decision-engine-service/src/routes/telegram.py:688-718` - обновленный формат сообщения

## Test

```bash
cd decision-engine-service && uv run python -m py_compile src/routes/telegram.py && echo "Syntax OK"
```
