# Issue #600: Learning Loop Extension — 7 Variables

## Что изменено

### Миграция БД (045_module_bank_7_types.sql)
- Расширен check constraint для `module_bank.module_type` до 7 типов
- Добавлены 7 новых FK колонок в `hypotheses` для каждой переменной
- Сохранена обратная совместимость с legacy типами (hook/promise/proof)

### module_learning.py
- Добавлены константы `MODULE_VARIABLE_COLUMNS` и `LEGACY_MODULE_COLUMNS`
- Обновлен `GetModulesForCreativeOutput` для 7 переменных + legacy
- Обновлена функция `get_modules_for_creative` для извлечения всех 7 модулей

### component_learning.py
- Добавлена константа `CORE_VARIABLES` с 7 переменными из VISION.md
- Добавлены `ump_type` и `cta_style` в список отслеживаемых компонентов

## 7 Independent Variables (VISION.md)
1. `hook_mechanism` - как зацепить внимание
2. `angle_type` - эмоциональный угол
3. `message_structure` - структура нарратива
4. `ump_type` - уникальный механизм обещания
5. `promise_type` - тип обещания
6. `proof_type` - тип доказательства
7. `cta_style` - стиль призыва к действию

## Test

```bash
make test-unit 2>&1 | tail -5 && echo "OK: All tests passed"
```
