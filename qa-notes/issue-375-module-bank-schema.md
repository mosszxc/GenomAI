# QA Notes: Issue #375 - Module Bank Schema

## Summary
Created database schema for Modular Creative System - tables for storing reusable creative modules (Hook, Promise, Proof) with performance metrics and compatibility tracking.

## Changes Made

### New Tables
1. **module_bank** - stores reusable modules
   - module_type: hook | promise | proof
   - module_key: SHA256 hash for deduplication
   - content: JSONB with extracted fields
   - Metrics: sample_size, win_count, loss_count, total_spend, total_revenue
   - Generated columns: win_rate, avg_roi
   - Status: active | emerging | fatigued | dead

2. **module_compatibility** - pairwise compatibility scores
   - module_a_id, module_b_id (canonical ordering with CHECK constraint)
   - compatibility_score: generated from win_count/sample_size

### hypotheses Extensions
- hook_module_id, promise_module_id, proof_module_id (FK → module_bank)
- generation_mode: reformulation | modular
- review_status: pending_review | approved | rejected | auto_approved

## Test Evidence

### Migration Applied
```sql
-- Verified via execute_sql
SELECT column_name, is_generated FROM information_schema.columns
WHERE table_name = 'module_bank';
-- Result: 20 columns including win_rate (ALWAYS), avg_roi (ALWAYS)
```

### Constraints Verified
```sql
SELECT conname FROM pg_constraint WHERE conrelid = 'genomai.module_bank'::regclass;
-- module_bank_module_type_check
-- module_bank_module_type_module_key_key (UNIQUE)
-- module_bank_status_check
-- FKs to creatives, decomposed_creatives, avatars
```

### Indexes Created
- idx_module_bank_type_win_rate (WHERE status='active')
- idx_module_bank_exploration (WHERE sample_size < 5)
- idx_module_bank_source_creative
- idx_module_compatibility_a, idx_module_compatibility_b
- idx_hypotheses_pending_review, idx_hypotheses_generation_mode

## Files Changed
- `infrastructure/migrations/038_module_bank.sql` (new)
- `docs/SCHEMA_REFERENCE.md` (updated: v1.4.0 → v1.5.0)

## Next Steps (Phase 2+)
Per MODULAR_CREATIVE_SYSTEM.md:
1. `temporal/activities/module_extraction.py` - extract modules from decomposition
2. Integration in CreativePipelineWorkflow
3. ModularHypothesisWorkflow for combinatorial generation
