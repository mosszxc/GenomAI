# GenomAI System Test Results

**Date:** 2024-12-24
**Tested by:** Claude Code

---

## Executive Summary

| Component | Status | Issue |
|-----------|--------|-------|
| creative_ingestion_webhook | BROKEN | Unused Respond to Webhook + tableId bug |
| creative_decomposition_llm | BROKEN | Unused Respond to Webhook |
| idea_registry_create | BROKEN | Unused Respond to Webhook |
| decision_engine_mvp | BROKEN | Unused Respond to Webhook |
| hypothesis_factory_generate | BROKEN | Webhook not registered (404) |
| Outcome Ingestion Keitaro | INACTIVE | Not tested (workflow disabled) |
| Telegram Hypothesis Delivery | INACTIVE | Not tested (workflow disabled) |
| Decision Engine (Render API) | UNKNOWN | Not directly tested |

**Critical Finding:** All active n8n workflows are broken due to "Unused Respond to Webhook node" error.

---

## Database State (Supabase - genomai schema)

| Table | Rows | Notes |
|-------|------|-------|
| creatives | 7 | Test creatives registered |
| transcripts | 1 | Only 1 transcript created |
| decomposed_creatives | 2 | 2 decompositions exist |
| ideas | 104 | Many test ideas |
| decisions | 6 | 3 approve, 2 defer, 1 reject |
| decision_traces | 5 | Decision audit trail |
| hypotheses | 16 | Generated hypothesis texts |
| deliveries | 2 | Telegram deliveries recorded |
| event_log | 41 | System events |
| outcome_aggregates | 0 | No outcomes yet |
| raw_metrics_current | 0 | No Keitaro metrics |
| daily_metrics_snapshot | 0 | No snapshots |

### Event Log Summary

| Event Type | Count |
|------------|-------|
| DecisionMade | 15 |
| DecisionAborted | 12 |
| CreativeRegistered | 2 |
| IdeaRegistered | 2 |
| HypothesisGenerated | 2 |
| HypothesisDelivered | 1 |
| CreativeDecomposed | 1 |
| TranscriptCreated | 1 |
| RawMetricsObserved | 1 |
| DailyMetricsSnapshotCreated | 1 |

---

## Workflow Details

### 1. creative_ingestion_webhook (ID: dvZvUUmhtPzYOK7X)

**Status:** BROKEN
**Active:** Yes
**Webhook:** POST /webhook/ingest/creative

**Errors:**
1. `Unused Respond to Webhook node found in the workflow`
2. `tableId: [object Object]` - n8n Resource Locator format bug

**Root Cause:**
- The workflow has multiple branches from "Validation Check" node
- When validation fails, it routes to both "Error Response" AND "Emit CreativeIngestionRejected"
- n8n requires all webhook trigger paths to end with Respond to Webhook OR use `responseMode: "lastNode"`

**Fix Required:**
1. Change webhook trigger to use `responseMode: "lastNode"` OR
2. Ensure every branch ends with a Respond to Webhook node connected properly
3. Fix tableId from `{ "__rl": true, "value": "event_log", "mode": "name" }` to just `"event_log"`

---

### 2. creative_decomposition_llm (ID: mv6diVtqnuwr7qev)

**Status:** BROKEN
**Active:** Yes
**Webhook:** POST /webhook/a1b2c3d4-e5f6-7890-abcd-ef1234567890

**Error:** `Unused Respond to Webhook node found in the workflow`

**Root Cause:**
- Same issue - branches not properly connected to Respond to Webhook

**Flow:**
```
Webhook → Load Schema → LLM Call → Schema Validation
    → [Persist Transcript] → Emit TranscriptCreated → Merge Results → Success Response
    → [Persist Decomposed] → Emit CreativeDecomposed → Call Idea Registry → Merge Results
```

**Fix Required:**
- Ensure Merge Results properly collects from both branches before Success Response

---

### 3. idea_registry_create (ID: cGSyJPROrkqLVHZP)

**Status:** BROKEN
**Active:** Yes
**Webhook:** POST /webhook/idea-registry-create

**Error:** `Unused Respond to Webhook node found in the workflow`

**Flow:**
```
Webhook → Validate Input → Load Decomposed → Canonical Hash → Idempotency Check
    → [Idea Found?]
        → Yes: Emit IdeaRegistered (Reuse) → Success Response
        → No: Create Idea → Emit IdeaRegistered (New) → Success Response
```

**Fix Required:**
- Both branches should properly connect to Success Response (they do, but connections may be broken)

---

### 4. decision_engine_mvp (ID: YT2d7z5h9bPy1R4v)

**Status:** BROKEN
**Active:** Yes
**Webhook:** POST /webhook/8a0b9e75-a8eb-4498-ace3-7a72fcf16e35

**Error:** `Unused Respond to Webhook node found in the workflow`

**Flow:**
```
Webhook/Manual → Validate Input → Load Config → Extract Config
    → Call Render API → Emit DecisionMade → Success Response
```

**Notes:**
- Calls external Render API at `https://genomai.onrender.com/api/decision`
- Decision Engine service needs to be verified separately

---

### 5. hypothesis_factory_generate (ID: oxG1DqxtkTGCqLZi)

**Status:** BROKEN
**Active:** Yes (but webhook not registered)
**Webhook:** POST /webhook/hypothesis-factory-trigger

**Error:** `404 - The requested webhook "POST hypothesis-factory-trigger" is not registered`

**Root Cause:**
- Workflow is marked active but webhook endpoint is not being served
- Possible version mismatch between saved and active version

**Notes:**
- Has 16 hypotheses in database - worked previously
- Contains Decision Guard that only processes "approve" decisions

---

### 6. Outcome Ingestion Keitaro (ID: zMHVFT2rM7PpTiJj)

**Status:** INACTIVE (not tested)
**Active:** No
**Trigger:** Schedule + Manual

**Flow:**
```
Schedule/Manual → Load Keitaro Config → Get All Campaigns → Extract IDs
    → Loop Over Campaigns → Get Metrics → Check Has Data
        → Aggregate → Persist Raw Metrics → Check Exists
            → Update/Create Raw Metrics → Emit RawMetricsObserved
                → Create Daily Snapshot → Emit DailyMetricsSnapshotCreated
```

**Notes:**
- Has 17 nodes - complex workflow
- Requires Keitaro API configuration (exists in keitaro_config table)
- Currently no data in raw_metrics_current or daily_metrics_snapshot

---

### 7. Telegram Hypothesis Delivery (ID: 5q3mshC9HRPpL6C0)

**Status:** INACTIVE (not tested)
**Active:** No

**Flow:**
```
Webhook → Parse Webhook → Load Hypotheses → Format Message
    → Send Telegram Message → Persist Delivery → Emit HypothesisDelivered
```

**Notes:**
- Has 2 deliveries recorded in database - worked previously
- Requires Telegram bot credentials

---

## Required Fixes (Priority Order)

### HIGH PRIORITY

1. **Fix "Unused Respond to Webhook" error in all workflows**
   - Option A: Set `responseMode: "lastNode"` on all webhook triggers
   - Option B: Ensure every execution path ends with Respond to Webhook node

2. **Fix tableId format bug**
   - Change from: `{ "__rl": true, "value": "table_name", "mode": "name" }`
   - Change to: `"table_name"` (string)
   - Affected nodes: All Supabase nodes in creative_ingestion_webhook

3. **Re-activate hypothesis_factory_generate webhook**
   - Deactivate and reactivate the workflow
   - Verify webhook path is correctly registered

### MEDIUM PRIORITY

4. **Activate and test Outcome Ingestion Keitaro**
   - Verify Keitaro API credentials
   - Test metrics collection

5. **Activate and test Telegram Hypothesis Delivery**
   - Verify Telegram bot credentials
   - Test message delivery

### LOW PRIORITY

6. **Verify Decision Engine Render service**
   - Test `/api/decision` endpoint directly
   - Verify all 4 checks work correctly

---

## Expected Flow (End-to-End)

```
1. User submits video URL + tracker_id
   └─► creative_ingestion_webhook
       └─► Creates creative in DB
       └─► Emits CreativeRegistered event

2. Decomposition triggered
   └─► creative_decomposition_llm
       └─► LLM classifies transcript to Canonical Schema
       └─► Saves transcript + decomposed_creative
       └─► Calls idea_registry_create

3. Idea registered
   └─► idea_registry_create
       └─► Generates canonical_hash
       └─► Creates/reuses idea
       └─► Emits IdeaRegistered event

4. Decision made
   └─► decision_engine_mvp
       └─► Calls Render API with idea_id
       └─► Render runs 4 checks (schema, death, fatigue, risk)
       └─► Returns APPROVE/REJECT/DEFER
       └─► Saves decision + trace
       └─► Emits DecisionMade event

5. Hypothesis generated (if APPROVE)
   └─► hypothesis_factory_generate
       └─► Loads decomposed creative
       └─► LLM generates hypothesis text
       └─► Saves hypothesis
       └─► Emits HypothesisGenerated event

6. Telegram delivery
   └─► Telegram Hypothesis Delivery
       └─► Formats message
       └─► Sends to Telegram
       └─► Records delivery

7. Outcome collection (scheduled)
   └─► Outcome Ingestion Keitaro
       └─► Pulls metrics from Keitaro
       └─► Updates raw_metrics_current
       └─► Creates daily snapshots
```

---

## Test Commands

```bash
# Test creative ingestion (currently broken)
curl -X POST "https://kazamaqwe.app.n8n.cloud/webhook/ingest/creative" \
  -H "Content-Type: application/json" \
  -d '{"video_url": "https://example.com/test.mp4", "tracker_id": "KT-001", "source_type": "user"}'

# Test decomposition (currently broken)
curl -X POST "https://kazamaqwe.app.n8n.cloud/webhook/a1b2c3d4-e5f6-7890-abcd-ef1234567890" \
  -H "Content-Type: application/json" \
  -d '{"creative_id": "UUID", "transcript_text": "..."}'

# Test decision engine (currently broken)
curl -X POST "https://kazamaqwe.app.n8n.cloud/webhook/8a0b9e75-a8eb-4498-ace3-7a72fcf16e35" \
  -H "Content-Type: application/json" \
  -d '{"idea_id": "UUID"}'

# Test Render API directly
curl -X POST "https://genomai.onrender.com/api/decision" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer API_KEY" \
  -d '{"idea_id": "UUID"}'
```

---

## Next Steps

1. Fix workflow connection issues in n8n UI
2. Re-test each workflow individually
3. Test full end-to-end flow
4. Activate inactive workflows
5. Set up monitoring/alerting
