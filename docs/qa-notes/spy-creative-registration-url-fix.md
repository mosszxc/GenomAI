# QA Notes: Spy Creative Registration URL Fix

**Issue:** #197
**Date:** 2025-12-31
**Status:** Fixed & Closed

## Problem

Insert Spy Creative node (id: `insert-creative`) in workflow `pL6C4j1uiJLfVRIi` was broken.

**Validation error:** `Required property 'URL' cannot be empty`

## Root Cause

HTTP Request node had only `jsonBody` parameter. Missing:
- `method`
- `url`
- `sendHeaders`
- `headerParameters`
- `sendBody`
- `specifyBody`

This was likely caused by incomplete fix in #178.

## Fix Applied

```json
{
  "method": "POST",
  "url": "https://ftrerelppsnbdcmtcwya.supabase.co/rest/v1/creatives",
  "sendHeaders": true,
  "headerParameters": {
    "parameters": [
      {"name": "apikey", "value": "..."},
      {"name": "Authorization", "value": "Bearer ..."},
      {"name": "Content-Profile", "value": "genomai"},
      {"name": "Prefer", "value": "return=representation"}
    ]
  },
  "sendBody": true,
  "specifyBody": "json",
  "jsonBody": "={{ JSON.stringify({...}) }}"
}
```

## Stuck Creatives

7 records with `status: unsupported_source`:
- All had test URLs (test-issue-178, test-url-fix, etc.)
- Marked as `status: test_data` (not real videos)

## Gotchas

### 1. n8n_update_partial_workflow requires `updates` key
```javascript
// WRONG
{ "type": "updateNode", "nodeId": "x", "parameters": {...} }

// CORRECT
{ "type": "updateNode", "nodeId": "x", "updates": { "parameters": {...} } }
```

### 2. Duplicate headers can occur
When updating node parameters, previous values may be preserved if not explicitly overwritten. Resulted in duplicate `Authorization` header.

### 3. Check Buyer Registered node missing schema header
Node queries `buyers` table but lacks `Accept-Profile: genomai` header. Works because `buyers` is in public schema (not genomai), but inconsistent.

## Verification

- Workflow validation: 0 errors, 21 warnings (non-critical)
- Node parameters verified via `n8n_get_workflow`
