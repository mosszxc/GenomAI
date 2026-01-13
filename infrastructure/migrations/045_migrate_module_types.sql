-- Migration: 045_migrate_module_types
-- Issue: #598
-- Purpose: Migrate module_type values from old to new naming convention
--   hook → hook_mechanism
--   promise → promise_type
--   proof → proof_type

-- ============================================================================
-- Step 1: Update existing data (if any)
-- ============================================================================
UPDATE genomai.module_bank SET module_type = 'hook_mechanism' WHERE module_type = 'hook';
UPDATE genomai.module_bank SET module_type = 'promise_type' WHERE module_type = 'promise';
UPDATE genomai.module_bank SET module_type = 'proof_type' WHERE module_type = 'proof';

-- ============================================================================
-- Step 2: Drop old CHECK constraint and add new one
-- ============================================================================
ALTER TABLE genomai.module_bank DROP CONSTRAINT IF EXISTS module_bank_module_type_check;

ALTER TABLE genomai.module_bank ADD CONSTRAINT module_bank_module_type_check
    CHECK (module_type IN ('hook_mechanism', 'promise_type', 'proof_type'));

-- ============================================================================
-- Comments
-- ============================================================================
COMMENT ON COLUMN genomai.module_bank.module_type IS 'Module type: hook_mechanism, promise_type, or proof_type';
