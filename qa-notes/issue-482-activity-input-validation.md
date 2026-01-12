# Issue #482: Input Validation for Activities

## Что изменено

- Добавлен модуль `temporal/models/validators.py` с переиспользуемыми валидаторами:
  - `validate_uuid()` - валидация UUID формата
  - `validate_sha256_hash()` - валидация SHA256 хэша (64 hex символа)
  - `validate_url()` - валидация HTTP/HTTPS URL
  - `validate_optional_uuid()` - валидация опционального UUID
  - `validate_enum()` - валидация значения из набора допустимых
  - `validate_dict_payload()` - валидация что payload является dict

- Добавлен модуль `temporal/models/supabase_inputs.py` с Pydantic моделями для будущего использования

- Добавлена валидация входных параметров во все activities в `temporal/activities/supabase.py`:
  - `create_creative` - video_url, source_type, buyer_id
  - `create_historical_creative` - video_url, buyer_id, tracker_id
  - `get_creative` - creative_id
  - `get_idea` - idea_id
  - `check_idea_exists` - canonical_hash
  - `create_idea` - canonical_hash, decomposed_creative_id, buyer_id, avatar_id
  - `upsert_idea` - canonical_hash, decomposed_creative_id, buyer_id, avatar_id
  - `save_decomposed_creative` - creative_id, canonical_hash, transcript_id, payload
  - `update_creative_status` - creative_id, status
  - `emit_event` - event_type, entity_id
  - `save_transcript` - creative_id, transcript_text
  - `get_existing_transcript` - creative_id

- Добавлены unit-тесты для валидаторов (35 тестов)

## Test

```bash
cd .worktrees/issue-482-arch-high-нет-валидации-input-parameters/decision-engine-service && python3 -m pytest tests/unit/test_activity_validators.py -v && echo "PASSED"
```
