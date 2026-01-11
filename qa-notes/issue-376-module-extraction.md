# QA Notes: Issue #376 - Module Extraction Activity

## Summary
Created Temporal activity for extracting Hook, Promise, Proof modules from decomposed payload.

## Files Changed
- `decision-engine-service/temporal/activities/module_extraction.py` (new)
- `decision-engine-service/temporal/activities/__init__.py` (modified)
- `decision-engine-service/tests/unit/test_module_extraction.py` (new)

## Implementation Details

### Activities Created
| Activity | Purpose |
|----------|---------|
| `extract_modules_from_decomposition` | Main activity - extracts all 3 module types |
| `get_creative_metrics` | Fetch metrics from outcome_aggregates for cold start |
| `upsert_module` | Insert/update module with deduplication |

### Module Types and Key Fields
| Type | Key Fields (for deduplication) |
|------|-------------------------------|
| hook | `hook_mechanism`, `opening_type` |
| promise | `promise_type`, `core_belief`, `state_before`, `state_after` |
| proof | `proof_type`, `proof_source` |

### Deduplication Logic
- SHA256 hash of key_fields creates `module_key`
- UNIQUE constraint on `(module_type, module_key)`
- On conflict: update metrics only if new creative has more data

### Cold Start Strategy
- New modules inherit metrics from source creative
- Metrics fetched from `outcome_aggregates` table

## Test Results

```
Unit Tests: 20 passed, 0 failed

tests/unit/test_module_extraction.py::TestComputeModuleKey (6 tests) - PASSED
tests/unit/test_module_extraction.py::TestExtractModuleContent (5 tests) - PASSED
tests/unit/test_module_extraction.py::TestGetTextContent (5 tests) - PASSED
tests/unit/test_module_extraction.py::TestModuleFieldsDefinition (4 tests) - PASSED
```

## Pre-commit Hooks
- ruff lint: PASSED
- ruff format: PASSED
- critical tests (hashing): PASSED
- all unit tests: PASSED

## Dependencies
- Requires migration #375 (module_bank schema) - VERIFIED EXISTS

## Next Steps
- Issue #377: Integration into CreativePipelineWorkflow
- Issue #378: Module learning activity
