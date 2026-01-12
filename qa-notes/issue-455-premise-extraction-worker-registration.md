# Issue #455: PremiseExtractionWorkflow not registered on knowledge worker

## Problem
PremiseExtractionWorkflow failed with error:
```
Workflow class PremiseExtractionWorkflow is not registered on this worker
```

## Root Cause
`temporal/worker.py` defined `knowledge_worker` with only:
- KnowledgeIngestionWorkflow
- KnowledgeApplicationWorkflow

Missing:
- PremiseExtractionWorkflow
- BatchPremiseExtractionWorkflow

## Fix
Added to `knowledge_worker` in `temporal/worker.py`:

**Workflows:**
- PremiseExtractionWorkflow
- BatchPremiseExtractionWorkflow

**Activities:**
- load_creative_data
- extract_premises_via_llm
- upsert_premise_and_learning
- emit_premise_extraction_event

## Files Changed
- `decision-engine-service/temporal/worker.py`

## Testing
- Unit tests: PASSED (35 tests)
- Pre-commit hooks: PASSED (ruff lint, format, critical tests)
- Pre-push hooks: PASSED (all unit tests)
- Deploy: PASSED (status: live)

## Production Verification
Deploy successful at 2026-01-12T08:48:20Z.
Full workflow test requires Temporal client trigger - will be verified on next PremiseExtractionWorkflow execution.

## PR
https://github.com/mosszxc/GenomAI/pull/456
