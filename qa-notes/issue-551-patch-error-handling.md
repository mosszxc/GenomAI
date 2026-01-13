# Issue #551: Silent failure при патче decomposed_creative

## Что изменено

- Добавлена проверка результата PATCH операций в `temporal/activities/supabase.py`
- Все 4 PATCH операции теперь вызывают `raise_for_status()` для проброса HTTP ошибок
- Затронутые функции: `create_idea`, `upsert_idea`, `update_creative_status`

## Места исправлений

1. `create_idea`: строка 346-350 — PATCH для связывания decomposed_creative с idea
2. `upsert_idea` (created path): строка 424-428 — PATCH при создании новой idea
3. `upsert_idea` (existing path): строка 450-454 — PATCH при нахождении существующей idea
4. `update_creative_status`: строка 564-568 — PATCH для обновления статуса креатива

## Test

```bash
cd /Users/mosszxc/Documents/Проэкты/GenomAI/.worktrees/issue-551-critical-silent-failure-при-патче-decomp/decision-engine-service && grep -c "patch_response.raise_for_status()" temporal/activities/supabase.py | grep -q "4" && echo "OK: all 4 PATCH operations now check for errors"
```
