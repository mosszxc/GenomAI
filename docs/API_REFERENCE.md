# API Reference

Decision Engine Service REST API documentation.

**Base URL:** `https://genomai.onrender.com`
**Auth:** `Authorization: Bearer {API_KEY}`

---

## Health Check

```
GET /health
```

No auth required.

**Response:**
```json
{
  "status": "ok",
  "timestamp": "2025-12-26T18:00:00.000000"
}
```

---

## Decision Engine

### Make Decision

```
POST /api/decision/
Authorization: Bearer {API_KEY}
```

**Request:**
```json
{
  "idea_id": "uuid"
}
```

**Response:**
```json
{
  "success": true,
  "decision": {
    "decision_id": "uuid",
    "idea_id": "uuid",
    "decision_type": "APPROVE|REJECT|DEFER",
    "decision_reason": "all_checks_passed|schema_invalid|idea_dead|fatigue_constraint|risk_budget_exceeded",
    "passed_checks": ["schema_validity", "death_memory", "fatigue_constraint", "risk_budget"],
    "failed_checks": [],
    "timestamp": "2025-12-26T18:00:00.000000"
  },
  "decision_trace": {
    "id": "uuid",
    "decision_id": "uuid",
    "checks": [
      {"check_name": "schema_validity", "order": 1, "result": "PASSED", "details": {}},
      {"check_name": "death_memory", "order": 2, "result": "PASSED", "details": {}},
      {"check_name": "fatigue_constraint", "order": 3, "result": "PASSED", "details": {}},
      {"check_name": "risk_budget", "order": 4, "result": "PASSED", "details": {}}
    ],
    "result": "APPROVE"
  }
}
```

---

## Schema Validator

### Validate LLM Output

```
POST /api/schema/validate
Authorization: Bearer {API_KEY}
Content-Type: application/json
```

Validates a payload against the idea JSON Schema.

**Request:**
```json
{
  "payload": {
    "angle_type": "pain",
    "core_belief": "problem_is_serious",
    "promise_type": "instant",
    "emotion_primary": "fear",
    "emotion_intensity": "high",
    "message_structure": "problem_solution",
    "opening_type": "shock_statement",
    "state_before": "unsafe",
    "state_after": "safe",
    "context_frame": "institutional",
    "source_type": "internal",
    "risk_level": "low",
    "horizon": "T1",
    "schema_version": "v1"
  },
  "schema_version": "v1"
}
```

**Response (valid):**
```json
{
  "valid": true,
  "errors": [],
  "warnings": []
}
```

**Response (invalid):**
```json
{
  "valid": false,
  "errors": [
    {
      "field": "angle_type",
      "message": "Invalid value. Allowed values: ['pain', 'fear', 'hope', 'curiosity', 'authority', 'social_proof', 'urgency', 'identity']",
      "code": "INVALID_ENUM_VALUE",
      "value": "INVALID"
    },
    {
      "field": "core_belief",
      "message": "Missing required field(s): core_belief, promise_type, ...",
      "code": "MISSING_REQUIRED_FIELD",
      "value": null
    }
  ],
  "warnings": []
}
```

### Error Codes

| Code | Description |
|------|-------------|
| `MISSING_REQUIRED_FIELD` | Required field is missing |
| `TYPE_MISMATCH` | Value has wrong type |
| `INVALID_ENUM_VALUE` | Value not in allowed enum |
| `INVALID_FORMAT` | Value doesn't match format (e.g., uuid) |
| `UNEXPECTED_FIELD` | Field not defined in schema |
| `EMPTY_PAYLOAD` | Payload is empty or null |
| `INVALID_SCHEMA_VERSION` | Unknown schema version |

### Supported Schema Versions

| Version | File | Description |
|---------|------|-------------|
| `v1` | `idea_schema_v1.json` | Base idea schema with 14 required fields |
| `v2` | `idea_schema_v2.json` | Extended schema (if exists) |

### Required Fields (v1)

| Field | Allowed Values |
|-------|----------------|
| `angle_type` | pain, fear, hope, curiosity, authority, social_proof, urgency, identity |
| `core_belief` | problem_is_serious, problem_is_hidden, solution_is_simple, solution_is_safe, solution_is_scientific, solution_is_unknown, others_have_this_problem, doctors_are_wrong, time_is_running_out |
| `promise_type` | instant, gradual, effortless, hidden, scientific, guaranteed, preventive |
| `emotion_primary` | fear, relief, anger, hope, curiosity, shame, trust |
| `emotion_intensity` | low, medium, high |
| `message_structure` | problem_solution, story_reveal, myth_debunk, authority_proof, question_answer, before_after, confession |
| `opening_type` | shock_statement, direct_question, personal_story, authority_claim, visual_pattern_break |
| `state_before` | unsafe, uncertain, powerless, ignorant, overwhelmed, excluded, dissatisfied |
| `state_after` | safe, confident, in_control, informed, calm, included, satisfied |
| `context_frame` | institutional, anti_authority, peer_based, expert_led, personal_confession, ironic |
| `source_type` | internal, spy, human_override, epistemic_shock |
| `risk_level` | low, medium, high |
| `horizon` | T1, T2, T3 |
| `schema_version` | v1 |

### Usage from n8n

```json
{
  "method": "POST",
  "url": "https://genomai.onrender.com/api/schema/validate",
  "authentication": "predefinedCredentialType",
  "nodeCredentialType": "httpHeaderAuth",
  "sendHeaders": true,
  "headerParameters": {
    "parameters": [
      { "name": "Content-Type", "value": "application/json" }
    ]
  },
  "sendBody": true,
  "specifyBody": "json",
  "jsonBody": "={{ JSON.stringify({ payload: $json, schema_version: 'v1' }) }}"
}
```

**Note:** The `creative_decomposition_llm` workflow uses a Code node for validation that does more than JSON Schema validation:
- Parses LLM output (handles markdown, JSON extraction)
- Normalizes field names (camelCase → snake_case)
- Validates v3 schema with optional fields
- Handles lenient validation for optional fields

For simple v1 schema validation, use this API. For complex LLM output processing, keep the Code node.

---

## Learning Loop

### Process Learning

```
POST /learning/process
Authorization: Bearer {API_KEY}
```

**Request:**
```json
{
  "idea_id": "uuid",
  "outcome_aggregate_id": "uuid"
}
```

**Response:**
```json
{
  "success": true,
  "updated_ideas": 1
}
```

### Get Status

```
GET /learning/status
Authorization: Bearer {API_KEY}
```

**Response:**
```json
{
  "status": "ok",
  "last_run": "2025-12-26T18:00:00.000000"
}
```

---

## Idea Registry

### Create Idea

```
POST /api/idea-registry/create
Authorization: Bearer {API_KEY}
```

**Request:**
```json
{
  "creative_id": "uuid",
  "schema_version": "v1"
}
```

---

## Recommendations

### List Pending Recommendations

```
GET /recommendations/
Authorization: Bearer {API_KEY}
```

**Query params:**
- `buyer_id` (optional) - Filter by buyer

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "buyer_id": "uuid",
      "avatar_id": "uuid",
      "geo": "US",
      "mode": "exploitation",
      "recommended_components": {"hook_mechanism": "confession", "angle_type": "pain"},
      "description": "Use proven components: confession hook (85%), pain angle (72%)",
      "status": "pending",
      "creative_id": null,
      "decision_id": null,
      "created_at": "2025-01-15T12:00:00Z"
    }
  ]
}
```

### Get Recommendation by ID

```
GET /recommendations/{id}
Authorization: Bearer {API_KEY}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "buyer_id": "uuid",
    "avatar_id": "uuid",
    "geo": "US",
    "mode": "exploitation",
    "recommended_components": {"hook_mechanism": "confession"},
    "description": "Use proven components...",
    "status": "executed",
    "creative_id": "uuid",
    "decision_id": "uuid",
    "created_at": "2025-01-15T12:00:00Z",
    "executed_at": "2025-01-15T14:00:00Z"
  }
}
```

**Note:** `decision_id` is populated when the recommendation has been executed (has `creative_id`) and the creative has been processed through the Decision Engine.

### Generate Recommendation

```
POST /recommendations/generate
Authorization: Bearer {API_KEY}
```

**Request:**
```json
{
  "buyer_id": "uuid",
  "avatar_id": "uuid",
  "geo": "US",
  "vertical": "nutra",
  "force_exploration": false
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "mode": "exploitation",
    "exploration_type": null,
    "description": "Use proven components: confession hook (85%)",
    "avg_confidence": 0.78,
    "components": [
      {
        "type": "hook_mechanism",
        "value": "confession",
        "confidence": 0.85,
        "sample_size": 42,
        "is_exploration": false
      }
    ]
  }
}
```

### Mark Recommendation Executed

```
POST /recommendations/{id}/executed
Authorization: Bearer {API_KEY}
```

**Request:**
```json
{
  "creative_id": "uuid"
}
```

### Record Recommendation Outcome

```
POST /recommendations/{id}/outcome
Authorization: Bearer {API_KEY}
```

**Request:**
```json
{
  "was_successful": true,
  "cpa": 12.50,
  "spend": 100.00,
  "revenue": 250.00
}
```

---

## Outcome Service

### Aggregate Outcome

```
POST /api/outcomes/aggregate
Authorization: Bearer {API_KEY}
Content-Type: application/json
```

Aggregates outcome metrics from a daily snapshot and triggers Learning Loop.

**Request:**
```json
{
  "snapshot_id": "uuid"
}
```

**Response (success):**
```json
{
  "success": true,
  "outcome": {
    "id": "uuid",
    "creative_id": "uuid",
    "decision_id": "uuid",
    "window_id": "D1",
    "window_start": "2025-01-01",
    "window_end": "2025-01-02",
    "conversions": 10,
    "spend": 50.00,
    "cpa": 5.00,
    "origin_type": "system",
    "learning_applied": false
  },
  "learning_triggered": true
}
```

**Response (no idea found):**
```json
{
  "success": false,
  "error": {
    "code": "IDEA_NOT_FOUND",
    "message": "No idea found for tracker abc123"
  }
}
```

**Response (no approved decision):**
```json
{
  "success": false,
  "error": {
    "code": "NO_APPROVED_DECISION",
    "message": "No APPROVE decision found for idea xyz789"
  }
}
```

### Window ID Calculation

| Window | Days Since Decision | Purpose |
|--------|---------------------|---------|
| D1 | 0-1 | Early signal |
| D3 | 2-3 | Short-term performance |
| D7 | 4-7 | Week performance |
| D7+ | 8+ | Long-term performance |

### Business Rules

1. **Only APPROVED ideas** get outcomes aggregated
2. **Window ID** based on days since decision
3. **origin_type** distinguishes:
   - `system` - realtime from Keitaro poller
   - `historical` - imported historical data
4. **learning_applied** - set to true by Learning Loop after processing
5. **CPA calculation**: `spend / conversions` (null if zero conversions)

### Usage from n8n

```json
{
  "method": "POST",
  "url": "https://genomai.onrender.com/api/outcomes/aggregate",
  "authentication": "predefinedCredentialType",
  "nodeCredentialType": "httpHeaderAuth",
  "sendHeaders": true,
  "headerParameters": {
    "parameters": [
      { "name": "Content-Type", "value": "application/json" }
    ]
  },
  "sendBody": true,
  "specifyBody": "json",
  "jsonBody": "={{ JSON.stringify({ snapshot_id: $json.body.snapshot_id }) }}"
}
```

---

## Historical Import

### Start Historical Import

```
POST /api/historical/start-import
```

Starts the HistoricalImportWorkflow to fetch campaigns from Keitaro and queue them for processing.

**Request:**
```json
{
  "buyer_id": "uuid",
  "keitaro_source": "tu",
  "date_from": "2025-12-01",
  "date_to": "2025-12-31"
}
```

**Response:**
```json
{
  "success": true,
  "workflow_id": "historical-import-{buyer_id}",
  "message": "Historical import started for source 'tu'"
}
```

**Notes:**
- `date_from` and `date_to` are optional (defaults to last 30 days by creation date)
- Fetches campaigns from Keitaro where campaign name contains `keitaro_source`
- Creates entries in `historical_import_queue` with status `pending_video`
- Each campaign can only be queued once (upsert on campaign_id)

### Submit Video for Historical Import

```
POST /api/historical/submit-video
```

Submits a video URL for a pending historical import campaign.

**Request:**
```json
{
  "campaign_id": "keitaro-campaign-123",
  "video_url": "https://example.com/video.mp4",
  "buyer_id": "uuid"
}
```

**Response:**
```json
{
  "success": true,
  "workflow_id": "historical-video-keitaro-campaign-123",
  "message": "Video processing started for campaign keitaro-campaign-123"
}
```

### Get Pending Imports

```
GET /api/historical/queue/{buyer_id}
```

Returns pending imports for a buyer.

**Response:**
```json
{
  "success": true,
  "count": 5,
  "imports": [
    {
      "id": "uuid",
      "campaign_id": "keitaro-123",
      "status": "pending_video",
      "metrics": {...}
    }
  ]
}
```

---

## Schedules API

Manage Temporal workflow schedules.

### List Schedules

```
GET /api/schedules
```

No auth required. Returns all Temporal schedules with status.

**Response:**
```json
{
  "success": true,
  "schedules": [
    {
      "id": "keitaro-poller",
      "status": "active",
      "interval": "10m",
      "cron": null,
      "last_run": "2026-01-10T16:50:00.070919+00:00",
      "next_run": "2026-01-10T17:00:00+00:00",
      "paused": false,
      "description": "Polls Keitaro for metrics every 10 minutes"
    }
  ]
}
```

### Get Schedule Details

```
GET /api/schedules/{schedule_id}
```

No auth required. Returns detailed info including paused state.

**Response:**
```json
{
  "success": true,
  "schedule": {
    "id": "keitaro-poller",
    "status": "active",
    "interval": "10m",
    "cron": null,
    "last_run": "2026-01-10T16:50:00.070919+00:00",
    "next_run": "2026-01-10T17:00:00+00:00",
    "paused": false,
    "description": "Polls Keitaro for metrics every 10 minutes"
  }
}
```

### Trigger Schedule

```
POST /api/schedules/{schedule_id}/trigger
X-API-Key: {API_KEY}
```

Manually trigger a schedule to run immediately.

**Response:**
```json
{
  "success": true,
  "message": "Schedule 'keitaro-poller' triggered successfully"
}
```

### Available Schedules

| ID | Interval/Cron | Description |
|----|---------------|-------------|
| `keitaro-poller` | 10m | Polls Keitaro for metrics |
| `metrics-processor` | 30m | Processes metrics into outcomes |
| `learning-loop` | 1h | Runs learning loop |
| `daily-recommendations` | 0 9 * * * | Daily recommendations at 09:00 UTC |
| `maintenance` | 6h | Cleanup and maintenance tasks |

---

## Knowledge Extraction

### Upload Source

```
POST /api/knowledge/sources
Authorization: Bearer {API_KEY}
```

Upload transcript for knowledge extraction.

**Request:**
```json
{
  "title": "Stefan Georgi - Hook Mastery",
  "content": "Full transcript text...",
  "source_type": "file",
  "url": null,
  "created_by": "291678304"
}
```

**Response:**
```json
{
  "workflow_id": "knowledge-ingest-abc123",
  "status": "processing"
}
```

### List Extractions

```
GET /api/knowledge/extractions?status=pending&limit=20
Authorization: Bearer {API_KEY}
```

**Response:**
```json
{
  "extractions": [...],
  "count": 5,
  "status_filter": "pending"
}
```

### Approve Extraction

```
POST /api/knowledge/extractions/{id}/approve
Authorization: Bearer {API_KEY}
```

Starts KnowledgeApplicationWorkflow to apply the knowledge.

**Request:**
```json
{
  "reviewed_by": "291678304"
}
```

**Response:**
```json
{
  "extraction_id": "uuid",
  "workflow_id": "knowledge-apply-abc123",
  "status": "applying"
}
```

### Reject Extraction

```
POST /api/knowledge/extractions/{id}/reject
Authorization: Bearer {API_KEY}
```

**Request:**
```json
{
  "reviewed_by": "291678304",
  "reason": "Not actionable"
}
```

**Response:**
```json
{
  "extraction_id": "uuid",
  "status": "rejected"
}
```

---

## Error Responses

All endpoints return errors in this format:

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message",
    "details": {}
  }
}
```

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad Request (validation error) |
| 401 | Unauthorized (missing/invalid API key) |
| 404 | Not Found |
| 500 | Internal Server Error |

---

## Swagger/OpenAPI

Interactive docs available at:
- `https://genomai.onrender.com/docs` (Swagger UI)
- `https://genomai.onrender.com/redoc` (ReDoc)
