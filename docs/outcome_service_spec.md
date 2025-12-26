# Outcome Service Specification

Migration spec for Outcome Aggregator from n8n to Python API.

## Table Schema

**Table:** `genomai.outcome_aggregates`

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | uuid | NO | gen_random_uuid() | Primary key |
| creative_id | uuid | NO | - | FK to creatives |
| decision_id | uuid | YES | - | FK to decisions |
| window_id | text | YES | - | D1, D3, D7, D7+ |
| window_start | date | NO | - | Decision date |
| window_end | date | NO | - | Snapshot date |
| impressions | integer | YES | - | Total impressions |
| conversions | integer | YES | - | Total conversions |
| spend | numeric | YES | - | Total spend |
| cpa | numeric | YES | - | Calculated CPA (generated?) |
| trend | text | YES | - | Performance trend |
| volatility | numeric | YES | - | Volatility score |
| environment_ctx | jsonb | YES | - | Environment context |
| origin_type | text | NO | - | "system" or "historical" |
| learning_applied | boolean | YES | false | Learning Loop processed |
| created_at | timestamp | NO | now() | Creation timestamp |

## Existing Workflow

**ID:** `243QnGrUSDtXLjqU`
**Name:** Outcome Aggregator
**Trigger:** Webhook POST `/webhook/outcome-aggregator`

### Flow

```
POST { snapshot_id }
  → Get Snapshot (daily_metrics_snapshot by id)
  → Get Idea (creative_idea_lookup by tracker_id)
  → [Guard: idea exists?]
      ├─ NO → Stop
      └─ YES → Get APPROVE Decision (decisions by idea_id)
               → [Guard: decision exists?]
                   ├─ NO → Stop
                   └─ YES → Calculate Window ID
                           → Insert outcome_aggregate
                           → Emit OutcomeAggregated
                           → Call Learning Loop
```

### Window ID Calculation

```javascript
const days = Math.floor((snapshotDate - decisionDate) / (1000 * 60 * 60 * 24));

if (days <= 1) return 'D1';
if (days <= 3) return 'D3';
if (days <= 7) return 'D7';
return 'D7+';
```

| Window | Days Since Decision | Purpose |
|--------|---------------------|---------|
| D1 | 0-1 | Early signal |
| D3 | 2-3 | Short-term performance |
| D7 | 4-7 | Week performance |
| D7+ | 8+ | Long-term performance |

### Input Contract

```json
POST /webhook/outcome-aggregator
{
  "snapshot_id": "uuid"
}
```

### Data Flow

1. **Snapshot** (`daily_metrics_snapshot`):
   - `id`, `tracker_id`, `date`
   - `metrics`: `{ conversions, cost, ... }`

2. **Idea Lookup** (`creative_idea_lookup`):
   - `tracker_id` → `idea_id`, `creative_id`

3. **Decision** (`decisions`):
   - `idea_id` + `decision = 'approve'` → `id`, `created_at`

4. **Output** (`outcome_aggregates`):
   - `creative_id`, `decision_id`, `window_id`
   - `window_start` (decision date), `window_end` (snapshot date)
   - `conversions`, `spend`
   - `origin_type` = "system"
   - `learning_applied` = false

### Integration: Learning Loop

After insert, calls:
```
POST https://kazamaqwe.app.n8n.cloud/webhook/learning-loop-v2
{
  "outcome_id": "uuid",
  "decision_id": "uuid",
  "idea_id": "uuid",
  "conversions": 10,
  "origin_type": "system"
}
```

## API Contract (Target)

### Aggregate Outcome

```
POST /api/outcomes/aggregate
Authorization: Bearer {API_KEY}
Content-Type: application/json

Request:
{
  "snapshot_id": "uuid"
}

Response (success):
{
  "success": true,
  "outcome": {
    "id": "uuid",
    "creative_id": "uuid",
    "decision_id": "uuid",
    "window_id": "D1",
    "conversions": 10,
    "spend": 50.00,
    "cpa": 5.00
  },
  "learning_triggered": true
}

Response (no idea found):
{
  "success": false,
  "error": {
    "code": "IDEA_NOT_FOUND",
    "message": "No idea found for tracker"
  }
}

Response (no approved decision):
{
  "success": false,
  "error": {
    "code": "NO_APPROVED_DECISION",
    "message": "No APPROVE decision found for idea"
  }
}
```

## Business Rules

1. **Only APPROVED ideas** get outcomes aggregated
2. **Window ID** based on days since decision
3. **origin_type** distinguishes:
   - `system` - realtime from Keitaro poller
   - `historical` - imported historical data
4. **learning_applied** - set to true by Learning Loop after processing
5. **CPA calculation**: `spend / conversions` (handle div by zero)

## Edge Cases

1. **No idea found** → Stop, no error (silent)
2. **No APPROVE decision** → Stop, no error (silent)
3. **Duplicate outcomes** → No constraint, multiple outcomes per creative/window possible
4. **Zero conversions** → CPA = null or infinity handling

## Migration Steps

1. Create `outcome_service.py` with aggregation logic
2. Add `/api/outcomes/aggregate` endpoint
3. Unit tests for window calculation and edge cases
4. Replace n8n workflow with HTTP Request to API
5. Verify Learning Loop integration

## Files

| File | Purpose |
|------|---------|
| `src/services/outcome_service.py` | Core aggregation logic |
| `src/routes/outcomes.py` | API endpoints |
| `tests/unit/test_outcome_service.py` | Unit tests |
