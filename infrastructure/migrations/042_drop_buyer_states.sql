-- 042_drop_buyer_states.sql
-- Remove deprecated buyer_states table
-- Issue #590: Table no longer used after Temporal migration

-- Drop trigger first
DROP TRIGGER IF EXISTS trigger_buyer_states_updated ON genomai.buyer_states;

-- Drop index
DROP INDEX IF EXISTS genomai.idx_buyer_states_updated;

-- Drop table
DROP TABLE IF EXISTS genomai.buyer_states;

-- Note: Function genomai.update_buyers_timestamp() is still used by genomai.buyers table
