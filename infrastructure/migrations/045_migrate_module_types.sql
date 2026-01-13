-- Migration: 045_migrate_module_types
-- Purpose: Map existing module types to new 7-variable system
-- Depends on: 038_module_bank (original schema), schema extension for 7 types
-- Related: Issue #598

-- ============================================================================
-- Data Migration: Map old types to new types
-- ============================================================================
-- hook → hook_mechanism
-- promise → promise_type
-- proof → proof_type

UPDATE genomai.module_bank
SET module_type = 'hook_mechanism'
WHERE module_type = 'hook';

UPDATE genomai.module_bank
SET module_type = 'promise_type'
WHERE module_type = 'promise';

UPDATE genomai.module_bank
SET module_type = 'proof_type'
WHERE module_type = 'proof';

-- ============================================================================
-- Verification query (run manually to confirm migration)
-- ============================================================================
-- SELECT module_type, COUNT(*) FROM genomai.module_bank GROUP BY module_type;
-- Expected: No rows with 'hook', 'promise', 'proof'

-- ============================================================================
-- Comments
-- ============================================================================
COMMENT ON TABLE genomai.module_bank IS 'Reusable creative modules with 7-variable types: hook_mechanism, angle_type, message_structure, ump_type, promise_type, proof_type, cta_style';
