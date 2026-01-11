-- Migration: 033_feature_experiments
-- Issue: #303 - Feature Experiments Infrastructure

-- Table: feature_experiments
-- Registry of experimental ML features with lifecycle management
CREATE TABLE IF NOT EXISTS genomai.feature_experiments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Identity
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    sql_definition TEXT NOT NULL,

    -- Lifecycle
    status TEXT DEFAULT 'shadow' CHECK (status IN ('shadow', 'active', 'deprecated')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    activated_at TIMESTAMPTZ,
    deprecated_at TIMESTAMPTZ,
    deprecation_reason TEXT,

    -- Validation metrics
    sample_size INT DEFAULT 0,
    correlation_cpa NUMERIC,
    correlation_updated_at TIMESTAMPTZ,

    -- Governance
    depends_on TEXT[] DEFAULT '{}',
    used_in TEXT[] DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_feature_experiments_status
ON genomai.feature_experiments(status);

CREATE INDEX IF NOT EXISTS idx_feature_experiments_name
ON genomai.feature_experiments(name);

COMMENT ON TABLE genomai.feature_experiments IS
'Registry of experimental ML features with shadow/active/deprecated lifecycle. Issue #303.';

-- Table: derived_feature_values
-- Computed feature values for entities
CREATE TABLE IF NOT EXISTS genomai.derived_feature_values (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    feature_name TEXT NOT NULL REFERENCES genomai.feature_experiments(name) ON DELETE CASCADE,
    entity_type TEXT NOT NULL CHECK (entity_type IN ('idea', 'outcome', 'creative')),
    entity_id UUID NOT NULL,
    value NUMERIC,
    computed_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE (feature_name, entity_type, entity_id)
);

CREATE INDEX IF NOT EXISTS idx_derived_features_lookup
ON genomai.derived_feature_values(feature_name, entity_type);

CREATE INDEX IF NOT EXISTS idx_derived_features_entity
ON genomai.derived_feature_values(entity_type, entity_id);

COMMENT ON TABLE genomai.derived_feature_values IS
'Computed feature values for ideas, outcomes, and creatives. Issue #303.';
