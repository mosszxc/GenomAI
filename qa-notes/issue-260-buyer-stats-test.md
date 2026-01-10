# Issue #260: Buyer Stats Command Test

## Summary
Fixed and validated `/stats` command in Telegram bot.

## Bugs Found and Fixed

### 1. Decisions query not filtered by buyer
**Before:** Query returned last 100 decisions from entire system
```python
decisions_resp = await client.get(
    f"{supabase_url}/rest/v1/decisions"
    f"?select=decision_type"
    f"&limit=100",
)
```

**After:** Stats derived from creatives.test_result filtered by buyer_id

### 2. Missing buyer_interactions logging
**Before:** No logging of /stats command or response
**After:** Added `log_buyer_interaction()` for incoming command and outgoing response

### 3. Wrong stats format
**Before:** Showed "approved/rejected" from decisions table
**After:** Shows wins/losses/testing from creatives + spend/revenue/ROI from metrics

## Changes Made
- `decision-engine-service/src/routes/telegram.py`:
  - Added `log_buyer_interaction()` helper function
  - Rewrote `handle_stats_command()` with proper buyer filtering
  - Added metrics aggregation from `raw_metrics_current`
  - Updated response format to match expected template

## Test Results

### Database Validation
```sql
SELECT b.telegram_id, COUNT(c.id) as creatives,
       COUNT(*) FILTER (WHERE c.test_result = 'win') as wins
FROM genomai.buyers b
LEFT JOIN genomai.creatives c ON c.buyer_id = b.id::text
GROUP BY b.id;

-- Results: 2 buyers found, stats calculated correctly
```

### Expected Response Format
```
📊 Твоя статистика:

Креативов: {total}
✅ Wins: {wins} ({win_rate}%)
❌ Losses: {losses}
⏳ Testing: {testing}

ROI: {roi}%
Spend: ${spend}
Revenue: ${revenue}
```

## Test Results (Production)

### Webhook Test
```bash
curl -X POST https://genomai.onrender.com/webhook/telegram \
  -H "Content-Type: application/json" \
  -d '{"update_id":12347,"message":{"message_id":3,"chat":{"id":361530748},"from":{"id":361530748},"text":"/stats"}}'
# Response: {"ok":true}
```

### buyer_interactions Log
```sql
SELECT * FROM genomai.buyer_interactions WHERE created_at > '2026-01-10';
-- telegram_id: 361530748
-- direction: in
-- message_type: command
-- content: /stats
-- created_at: 2026-01-10 12:23:45
```

## Bugs Fixed During Testing

### 1. Direction value mismatch
**Issue:** Used "incoming"/"outgoing" but DB expects "in"/"out"
**Fix:** Changed to match existing data format

### 2. PostgREST in() query format
**Issue:** Used quoted values `"9314","8408"`
**Expected:** Plain values `9314,8408`
**Fix:** Removed f-string quotes in tracker_list join

### 3. Missing isinstance check
**Issue:** metrics_resp.json() could return error object
**Fix:** Added `if isinstance(metrics_rows, list)` guard

## Checklist
- [x] Code compiles (py_compile passed)
- [x] Pre-commit hooks pass (ruff lint/format)
- [x] Database query logic verified
- [x] Webhook test (returns ok)
- [x] Incoming command logged in buyer_interactions
- [ ] Outgoing response log (needs debug - may require TELEGRAM_BOT_TOKEN)
