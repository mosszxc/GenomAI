-- Add approve_with_warnings to decisions CHECK constraint
-- Issue: #731

-- Drop the old constraint
ALTER TABLE genomai.decisions
DROP CONSTRAINT IF EXISTS decisions_decision_check;

-- Add updated constraint with approve_with_warnings
ALTER TABLE genomai.decisions
ADD CONSTRAINT decisions_decision_check
CHECK (decision IN ('approve', 'reject', 'defer', 'approve_with_warnings'));
