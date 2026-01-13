# Issue #588: fix: undocumented columns in buyers and buyer_interactions migrations

## Что изменено

- Добавлена колонка `keitaro_source TEXT` в миграцию `010_buyers.sql`
- Добавлена колонка `buyer_id UUID REFERENCES genomai.buyers(id)` в миграцию `012_buyer_interactions.sql`
- Добавлен индекс `idx_buyer_interactions_buyer_id` для колонки `buyer_id`

## Причина

Колонки существовали в БД и использовались в коде, но отсутствовали в базовых миграциях:
- `buyers.keitaro_source` — используется в `buyer.py:105` и функции `create_buyer_normalized`
- `buyer_interactions.buyer_id` — используется в `buyer.py:366-367` при логировании

При переразвёртывании БД с нуля колонки бы не создались.

## Test

```bash
grep -n 'keitaro_source' infrastructure/migrations/010_buyers.sql && grep -n 'buyer_id UUID' infrastructure/migrations/012_buyer_interactions.sql && echo "OK: columns documented"
```
