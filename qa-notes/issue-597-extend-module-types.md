# Issue #597 — Schema Migration — 7 Module Types

## Что изменено

- Создана миграция `V1.6.0__extend_module_types.sql`
- Расширен CHECK constraint `module_bank.module_type` с 3 до 10 значений:
  - 7 новых: `hook_mechanism`, `angle_type`, `message_structure`, `ump_type`, `promise_type`, `proof_type`, `cta_style`
  - 3 legacy (для обратной совместимости): `hook`, `promise`, `proof`
- Создан `decision-engine-service/src/types.py` с Python Enum `ModuleType`

## Файлы

- `infrastructure/migrations/V1.6.0__extend_module_types.sql`
- `decision-engine-service/src/types.py`

## Test

```bash
cd decision-engine-service && python3 -c "from src.types import ModuleType, MODULE_TYPES; assert len(MODULE_TYPES) == 7, 'Expected 7 types'; print('OK: 7 module types defined')"
```

## Ручная проверка миграции (Supabase)

```sql
-- После применения миграции:
INSERT INTO genomai.module_bank (module_type, module_key, content)
VALUES ('hook_mechanism', 'test-key', '{}');

-- Должно работать ✅

INSERT INTO genomai.module_bank (module_type, module_key, content)
VALUES ('invalid_type', 'test-key', '{}');

-- Должно дать ошибку constraint ✅
```

## Связанные issues

- Epic: #596
- Следующий: #598 (Data Migration)
