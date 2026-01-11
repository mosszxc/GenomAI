# QA Notes: Issue #297 - Correlation Discovery Command

## Summary
Added `/correlations` admin command to discover component synergies and conflicts.

## Changes
- **New file:** `decision-engine-service/src/services/correlation_discovery.py`
  - `discover_correlations()` - analyzes component pairs from decomposed_creatives + creatives
  - Calculates lift: P(win|A∩B) / (P(win|A) × P(win|B))
  - Categorizes as strong/weak positive/negative
  - `format_correlations_telegram()` - formats output for Telegram

- **Modified:** `decision-engine-service/src/routes/telegram.py`
  - Added `handle_correlations_command()` handler
  - Added to help message and command dispatch

## Test Execution
```
Webhook: POST /webhook/telegram
Payload: {"text": "/correlations", "from": {"id": 291678304}}
Response: {"ok": true}
```

## Verification
```sql
SELECT content FROM genomai.buyer_interactions
WHERE content LIKE '%correlations%' ORDER BY created_at DESC LIMIT 2;
```

**Result:**
- IN: `/correlations`
- OUT: "🔗 Correlation Discovery\n\nNo significant correlations found yet.\n\nNeed more test results to discover patterns.\nMinimum samples: 5 per pair"

## Expected Behavior
- With test data: Shows strong positive/negative correlations with lift percentages
- Without test data: Shows "No significant correlations found yet" message

## Example Output (when data available)
```
🔗 Discovered Correlations

Strong positive:
├── hope + question_opening → +23% lift
└── curiosity + story_structure → +18% lift

Strong negative:
├── fear + guaranteed_promise → -31% penalty
└── urgency + long_form → -25% penalty

💡 Recommendation: Test hope + question combo
```

## Lift Thresholds
| Category | Lift Value | Meaning |
|----------|------------|---------|
| Strong positive | ≥1.15 | +15% synergy |
| Weak positive | ≥1.05 | +5% synergy |
| Weak negative | ≤0.95 | -5% conflict |
| Strong negative | ≤0.85 | -15% conflict |

## Requirements
- Min 5 samples per component pair
- Min 10 samples per individual component
- Admin only (telegram_id in ADMIN_TELEGRAM_IDS)
