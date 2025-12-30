# QA Notes: Add target_vertical/target_geo to creatives (#193)

## Summary

Добавлены поля `target_vertical` и `target_geo` в таблицу `creatives` для хранения контекста вертикали/гео на момент регистрации креатива.

---

## Changes Made

### Database
- Migration: `022_creative_target_context.sql`
- Added columns: `target_vertical TEXT`, `target_geo TEXT`
- Added index: `idx_creatives_target(target_vertical, target_geo)`

### Workflows Updated

| Workflow | ID | Changes |
|----------|-----|---------|
| Buyer Creative Registration | d5i9dB2GNqsbfmSD | Check Buyer: добавлен select verticals,geos; Insert: target_vertical/geo |
| Spy Creative Registration | pL6C4j1uiJLfVRIi | Check Buyer: добавлен select verticals,geos; Insert: target_vertical/geo |
| Zaliv Session Handler | 97cj3kRY6zzlAy0M | Parse Creative: добавлен buyer_verticals/geos; Register: target_vertical/geo |

---

## How Values Are Set

```javascript
target_vertical: ($json.verticals && $json.verticals[0]) || null
target_geo: ($json.geos && $json.geos[0]) || null
```

- Берётся **первый элемент** из массива `verticals[]` / `geos[]` баера
- Если массив пустой или отсутствует → `null`

---

## Test Verification

```sql
-- Check columns exist
SELECT column_name, data_type FROM information_schema.columns
WHERE table_schema = 'genomai' AND table_name = 'creatives'
AND column_name IN ('target_vertical', 'target_geo');
-- Result: target_vertical TEXT, target_geo TEXT ✓

-- Check index
SELECT indexname FROM pg_indexes
WHERE schemaname = 'genomai' AND indexname = 'idx_creatives_target';
-- Result: idx_creatives_target ✓

-- Check buyer data
SELECT name, verticals, geos FROM genomai.buyers WHERE name = 'TU';
-- Result: verticals=[POT, PROST], geos=[MX] ✓
```

---

## Edge Cases

1. **Buyer без verticals/geos** → target_vertical/geo = null
2. **Spy креатив** → берёт verticals/geos баера (если есть)
3. **Исторические креативы** → target_vertical/geo = null (не backfilled)
4. **Баер меняет verticals** → новые креативы получат новые значения, старые не меняются

---

## Future Improvements

- Backfill для существующих креативов (по buyer_id → buyers.verticals[0]/geos[0])
- При регистрации спрашивать у баера для какого vertical/geo (если несколько)
- Использовать target_vertical/geo в Learning Loop для правильной аттрибуции

---

## Files Changed

- `infrastructure/migrations/022_creative_target_context.sql`
- `docs/SCHEMA_REFERENCE.md` (schema v1.2.0)
- n8n: d5i9dB2GNqsbfmSD, pL6C4j1uiJLfVRIi, 97cj3kRY6zzlAy0M
