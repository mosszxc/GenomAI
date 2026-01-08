# QA Notes: Issue #194 - Geo in Avatar Canonical Hash

## Issue
**feat: Include geo in avatar canonical hash**

## Changes Made

### 1. n8n Workflow (`idea_registry_create` - cGSyJPROrkqLVHZP)
Updated "Canonical Hash" node to include geo in avatar hash:
```javascript
const avatarHashInput = [
  vertical,
  geo,  // NEW: Added for geo-specific avatars
  deepDesireType,
  primaryTrigger,
  awarenessLevel
].join('|');
```

### 2. Python Code
- `hashing.py`: Added `geo` parameter to `compute_avatar_hash()` function
- `avatar_service.py`: Updated `find_or_create_avatar()` to pass geo

## Breaking Change

**This is a BREAKING CHANGE.**

| Old Format | New Format |
|------------|------------|
| `vertical\|deep_desire\|trigger\|awareness` | `vertical\|geo\|deep_desire\|trigger\|awareness` |

### Impact on Existing Avatars
- Existing avatars have hashes computed WITHOUT geo
- New avatars will have different hashes even with same attributes
- Existing avatars will NOT match new lookups → new avatars will be created

### Mitigation
1. Existing avatars have `geo='unknown'` stored in DB
2. New entries with `geo=null/unknown` will create new avatars (different hash)
3. This is acceptable as it enables geo-specific avatar tracking going forward

## Verification

### Python Unit Test
```python
# Old format
old = hashlib.md5('nutra|deep|trigger|aware'.encode()).hexdigest()
# bef85eaa4121bb9b29d77a2d63e828b0

# New format with geo
new = compute_avatar_hash('nutra', 'RU', 'deep', 'trigger', 'aware')
# 1d9354c36cacb8e9f4b2121ab29da951

# Different hashes confirmed
assert old != new
```

### n8n Workflow
- Workflow updated and active
- Version: 147 (activeVersionId: 074901af-a1d5-4e1d-a4f1-fab1727d8f7c)

## Edge Cases / Gotchas

1. **Null geo handling**: Both n8n and Python default to `'unknown'` when geo is null
2. **Existing avatars**: Will not be matched by new hash lookups
3. **Python API path**: When `Use Python API?` flag is true, Python code handles hashing (now updated)
4. **n8n path**: When flag is false, n8n handles hashing (now updated)

## Files Modified

| File | Change |
|------|--------|
| n8n `idea_registry_create` | Added geo to avatar hash |
| `hashing.py` | Added geo parameter |
| `avatar_service.py` | Pass geo to hash function |

## Related
- Issue #194
- Workflow: `idea_registry_create` (cGSyJPROrkqLVHZP)
