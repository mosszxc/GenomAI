-- Migration: V1.6.0__extend_module_types
-- Purpose: Extend module_type from 3 to 7 values
-- Issue: #597 (Epic: #596)
--
-- Old types: hook, promise, proof (kept for backward compatibility)
-- New types: hook_mechanism, angle_type, message_structure, ump_type, promise_type, proof_type, cta_style
--
-- Note: Old types preserved until #598 (data migration) and #599 (code update) complete

-- ============================================================================
-- Drop old CHECK constraint and add new one with all values
-- ============================================================================

-- Drop the old constraint
ALTER TABLE genomai.module_bank
DROP CONSTRAINT IF EXISTS module_bank_module_type_check;

-- Add new constraint with 7 new module types + 3 legacy types
-- Legacy types (hook, promise, proof) kept for backward compatibility
-- Will be removed after #598 data migration completes
ALTER TABLE genomai.module_bank
ADD CONSTRAINT module_bank_module_type_check
CHECK (module_type IN (
    -- New 7 types (VISION.md)
    'hook_mechanism',
    'angle_type',
    'message_structure',
    'ump_type',
    'promise_type',
    'proof_type',
    'cta_style',
    -- Legacy types (backward compatibility, remove after #598)
    'hook',
    'promise',
    'proof'
));

-- ============================================================================
-- Comments
-- ============================================================================
COMMENT ON COLUMN genomai.module_bank.module_type IS 'Module type: hook_mechanism, angle_type, message_structure, ump_type, promise_type, proof_type, cta_style (legacy: hook, promise, proof)';
