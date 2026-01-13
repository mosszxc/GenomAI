-- Migration: 045_module_bank_7_types
-- Purpose: Extend module_bank and hypotheses to support 7 independent variables
-- Issue: #600 - Learning Loop Extension — 7 Variables
-- Epic: #596 - VISION Implementation — 7 Independent Variables
--
-- 7 Variables (from VISION.md):
-- 1. hook_mechanism
-- 2. angle_type
-- 3. message_structure
-- 4. ump_type
-- 5. promise_type
-- 6. proof_type
-- 7. cta_style

-- ============================================================================
-- 1. Extend module_bank.module_type to support 7 types
-- ============================================================================

-- Drop existing constraint
ALTER TABLE genomai.module_bank
DROP CONSTRAINT IF EXISTS module_bank_module_type_check;

-- Add new constraint with 7 types
ALTER TABLE genomai.module_bank
ADD CONSTRAINT module_bank_module_type_check
CHECK (module_type IN (
    'hook_mechanism',
    'angle_type',
    'message_structure',
    'ump_type',
    'promise_type',
    'proof_type',
    'cta_style',
    -- Keep legacy types for backward compatibility during migration
    'hook',
    'promise',
    'proof'
));

-- ============================================================================
-- 2. Add new module columns to hypotheses table
-- ============================================================================

-- Add 4 new module columns (3 legacy columns already exist)
ALTER TABLE genomai.hypotheses
ADD COLUMN IF NOT EXISTS hook_mechanism_module_id UUID REFERENCES genomai.module_bank(id),
ADD COLUMN IF NOT EXISTS angle_type_module_id UUID REFERENCES genomai.module_bank(id),
ADD COLUMN IF NOT EXISTS message_structure_module_id UUID REFERENCES genomai.module_bank(id),
ADD COLUMN IF NOT EXISTS ump_type_module_id UUID REFERENCES genomai.module_bank(id),
ADD COLUMN IF NOT EXISTS promise_type_module_id UUID REFERENCES genomai.module_bank(id),
ADD COLUMN IF NOT EXISTS proof_type_module_id UUID REFERENCES genomai.module_bank(id),
ADD COLUMN IF NOT EXISTS cta_style_module_id UUID REFERENCES genomai.module_bank(id);

-- ============================================================================
-- 3. Create indexes for new columns
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_hypotheses_hook_mechanism_module
ON genomai.hypotheses(hook_mechanism_module_id) WHERE hook_mechanism_module_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_hypotheses_angle_type_module
ON genomai.hypotheses(angle_type_module_id) WHERE angle_type_module_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_hypotheses_message_structure_module
ON genomai.hypotheses(message_structure_module_id) WHERE message_structure_module_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_hypotheses_ump_type_module
ON genomai.hypotheses(ump_type_module_id) WHERE ump_type_module_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_hypotheses_promise_type_module
ON genomai.hypotheses(promise_type_module_id) WHERE promise_type_module_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_hypotheses_proof_type_module
ON genomai.hypotheses(proof_type_module_id) WHERE proof_type_module_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_hypotheses_cta_style_module
ON genomai.hypotheses(cta_style_module_id) WHERE cta_style_module_id IS NOT NULL;

-- ============================================================================
-- 4. Index for module_bank by type (for faster lookups per variable)
-- ============================================================================

DROP INDEX IF EXISTS genomai.idx_module_bank_type_win_rate;

CREATE INDEX IF NOT EXISTS idx_module_bank_type_win_rate
ON genomai.module_bank(module_type, win_rate DESC)
WHERE status = 'active';

-- ============================================================================
-- 5. Comments
-- ============================================================================

COMMENT ON COLUMN genomai.hypotheses.hook_mechanism_module_id IS 'Module ID for hook_mechanism variable (how to grab attention)';
COMMENT ON COLUMN genomai.hypotheses.angle_type_module_id IS 'Module ID for angle_type variable (emotional angle)';
COMMENT ON COLUMN genomai.hypotheses.message_structure_module_id IS 'Module ID for message_structure variable (narrative structure)';
COMMENT ON COLUMN genomai.hypotheses.ump_type_module_id IS 'Module ID for ump_type variable (unique mechanism promise)';
COMMENT ON COLUMN genomai.hypotheses.promise_type_module_id IS 'Module ID for promise_type variable (type of promise)';
COMMENT ON COLUMN genomai.hypotheses.proof_type_module_id IS 'Module ID for proof_type variable (type of proof)';
COMMENT ON COLUMN genomai.hypotheses.cta_style_module_id IS 'Module ID for cta_style variable (call to action style)';
