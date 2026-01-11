# QA Notes: Issue #379 - Modular Hypothesis Generation

## Summary
Implemented modular hypothesis generation activity with 90/10 exploitation/exploration split.

## Changes

### New Files
| File | Purpose |
|------|---------|
| `src/services/module_selector.py` | Module selection with 90/10 split, compatibility scoring |
| `temporal/activities/modular_generation.py` | LLM synthesis from hook+promise+proof modules |
| `tests/unit/test_module_selector.py` | 21 unit tests for selector |
| `tests/unit/test_modular_generation.py` | 14 unit tests for generation |

### Modified Files
| File | Change |
|------|--------|
| `temporal/worker.py` | Register new activities |

## Key Features

### Module Selector (90/10 Split)
- **Exploitation (90%)**: Top modules by `win_rate` (status=active)
- **Exploration (10%)**: Under-explored modules (`sample_size < 5`)
- **Compatibility**: Combined score = 70% win_rate + 30% compatibility

### Modular Generation
- Selects hook → compatible promise → compatible proof
- LLM synthesizes coherent ad text from modules
- Saves hypothesis with:
  - `generation_mode = 'modular'`
  - `review_status = 'pending_review'`
  - Module references (`hook_module_id`, `promise_module_id`, `proof_module_id`)

### Minimum Requirements for Modular Generation
- 3+ active hooks
- 3+ active promises
- 2+ active proofs
- 2+ modules with sample_size >= 5

## Testing

### Unit Tests
```bash
pytest tests/unit/test_module_selector.py tests/unit/test_modular_generation.py -v
# 35 passed in 0.33s
```

### Integration Test (Manual)
```sql
-- Check modular readiness
SELECT module_type, COUNT(*), AVG(win_rate)
FROM genomai.module_bank
WHERE status = 'active'
GROUP BY module_type;

-- Check modular hypotheses
SELECT id, generation_mode, review_status, hook_module_id
FROM genomai.hypotheses
WHERE generation_mode = 'modular'
LIMIT 5;
```

## Dependencies
- Requires #375 (module_bank schema) - CLOSED
- Requires #376 (module extraction activity) - CLOSED

## Next Steps
- #380: ModularHypothesisWorkflow (orchestration)
- #381: Integration into CreativePipelineWorkflow
- #382: Human review UI in Telegram
