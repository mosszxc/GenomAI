# Issue #226: Hypothesis Factory не копирует buyer_id из creative

## Problem
Workflow `hypothesis_factory_generate` (oxG1DqxtkTGCqLZi) не копировал `buyer_id` из цепочки `creative → decomposed_creative → idea` при создании hypothesis.

**Влияние:** HypothesisDeliveryFailed с reason: "No buyer_id assigned"

## Root Cause
При INSERT в `hypotheses` через n8n workflow, `buyer_id` не извлекался из связанного creative.

## Solution
Database-level fix через trigger (не требует изменения n8n workflow):

1. **Function `genomai.get_buyer_id_for_idea(idea_id)`**
   - Lookup buyer_id через цепочку: idea → decomposed_creative → creative
   - Возвращает UUID или NULL

2. **Trigger `trg_hypothesis_set_buyer_id`**
   - BEFORE INSERT на `genomai.hypotheses`
   - Автоматически заполняет `buyer_id` если не указан

3. **Backfill** существующих hypotheses без buyer_id

## Verification
```sql
-- Тест trigger: INSERT без buyer_id
INSERT INTO genomai.hypotheses (id, idea_id, decision_id, content, prompt_version)
VALUES (gen_random_uuid(), '<idea_with_buyer>', '<decision_id>', 'test', 'v1')
RETURNING id, buyer_id;
-- buyer_id автоматически заполняется!

-- Проверка backfill
SELECT COUNT(*) FROM genomai.hypotheses WHERE buyer_id IS NULL;
-- Только hypotheses от creatives без buyer_id (spy, legacy)
```

## Type Mismatch Note
- `creatives.buyer_id` = TEXT (хранит UUID как строку)
- `hypotheses.buyer_id` = UUID

Function использует `::uuid` cast для преобразования.

## Files Changed
- `infrastructure/migrations/024_hypothesis_buyer_id_trigger.sql`

## Related
- Issue #222 (застрявший hypothesis)
- Telegram Hypothesis Delivery workflow
