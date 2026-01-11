-- Migration: Add statistical validation fields to feature_experiments
-- Issue: #306
--
-- Adds columns needed for statistical safeguards:
-- - p_value: for Bonferroni-corrected significance testing
-- - correlation_std_dev: for stability validation

ALTER TABLE genomai.feature_experiments
ADD COLUMN IF NOT EXISTS p_value NUMERIC,
ADD COLUMN IF NOT EXISTS correlation_std_dev NUMERIC;

COMMENT ON COLUMN genomai.feature_experiments.p_value IS
    'P-value from correlation test, used for Bonferroni significance validation';

COMMENT ON COLUMN genomai.feature_experiments.correlation_std_dev IS
    'Standard deviation of rolling correlations, used for stability validation';
