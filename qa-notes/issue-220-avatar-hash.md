# Issue #220: Avatar canonical_hash length

## Root Cause
E2E тест ошибочно проверял `avatars.canonical_hash` на 64 символа (SHA-256), но по дизайну используется MD5 (32 символа).

## Evidence
- `infrastructure/migrations/015_avatar_canonical.sql` line 111:
  ```sql
  COMMENT ON COLUMN genomai.avatars.canonical_hash IS
  'Unique fingerprint: MD5(vertical + deep_desire_type + primary_trigger + awareness_level).'
  ```
- `decision-engine-service/src/utils/hashing.py` line 100:
  ```python
  return hashlib.md5(avatar_hash_input.encode('utf-8')).hexdigest()
  ```

## Hash Lengths by Entity
| Entity | Algorithm | Length |
|--------|-----------|--------|
| ideas.canonical_hash | SHA-256 | 64 chars |
| avatars.canonical_hash | MD5 | 32 chars |

## Fix
Changed `.claude/commands/e2e.md` line 495:
- Before: `LENGTH(canonical_hash) != 64`
- After: `LENGTH(canonical_hash) != 32`

## Test
```sql
SELECT COUNT(*) FILTER (WHERE canonical_hash IS NOT NULL AND LENGTH(canonical_hash) != 32) as invalid_hash
FROM genomai.avatars;
-- Result: 0 (was 2 with wrong 64-char check)
```

## Lesson
Different entities can use different hash algorithms. Always verify expected format in migration comments and implementation code before flagging as data integrity issue.
