# Issue #579: INSERT операции без ON CONFLICT — дубликаты при retry

## Что изменено

- `module_extraction.py`: Добавлен `on_conflict=module_type,module_key` к INSERT в `module_bank`
- `supabase.py`: Добавлен `on_conflict=creative_id,version` к INSERT в `transcripts`
- Оба места используют `Prefer: resolution=ignore-duplicates` для идемпотентности
- При конфликте (retry case) возвращается существующая запись вместо ошибки

## Test

```bash
grep -n "on_conflict=" decision-engine-service/temporal/activities/module_extraction.py decision-engine-service/temporal/activities/supabase.py | grep -E "(module_bank|transcripts)" && echo "OK: on_conflict найден в обоих файлах"
```
