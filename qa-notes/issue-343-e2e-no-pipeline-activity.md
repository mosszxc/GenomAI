# Issue #343: E2E Info - No pipeline activity for 7 days

## Status: Expected Behavior

## Investigation Summary

E2E test (Phase 2) detected 0 transcripts and 0 ideas in last 7 days.

### Findings

1. **Database state (2026-01-11)**:
   - Creatives: 1 (created today)
   - Transcripts: 0
   - Ideas: 0

2. **Root cause analysis**:
   - Creative `c7818783-5feb-4c68-839f-dfbc569d960e` was created with:
     - `source_type = 'user'`
     - `buyer_id = null`
     - `status = 'registered'`
   - This is a **direct DB insert** (test data), not via workflow trigger

3. **How CreativePipelineWorkflow gets triggered**:
   - Telegram webhook → `CreativeRegistrationWorkflow` → `CreativePipelineWorkflow`
   - `/api/historical/submit-video` → `HistoricalVideoHandlerWorkflow` → `CreativePipelineWorkflow`
   - Direct INSERT into `creatives` table does **NOT** trigger workflow

4. **Service status**:
   - Render service: live (deployed 2026-01-11T13:38:45Z)
   - Health endpoint: OK
   - MaintenanceCompleted event at 12:00 UTC (Temporal working)

## Conclusion

Pipeline is functioning correctly. No activity because:
- No real creatives submitted through Telegram or API
- Test creative was inserted directly into DB without workflow trigger

## Recommendation

To test full pipeline:
```bash
# Via API
curl -X POST https://genomai.onrender.com/api/historical/submit-video \
  -H "Content-Type: application/json" \
  -d '{"campaign_id": "test", "video_url": "...", "buyer_id": "..."}'

# Via Telegram
# Send video URL to @GenomAIBot after /start
```

## Tested

- [x] DB queries verified state
- [x] Service health checked
- [x] Render logs reviewed
- [x] Workflow trigger paths traced

## Files Reviewed

- `decision-engine-service/src/routes/telegram.py`
- `decision-engine-service/src/routes/historical.py`
- `decision-engine-service/temporal/workflows/creative_pipeline.py`
