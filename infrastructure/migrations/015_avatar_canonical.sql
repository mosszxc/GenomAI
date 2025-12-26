-- Migration 015: Avatar Canonical Hash System
-- Enables automatic avatar detection from creative decomposition
--
-- New fields:
--   - deep_desire_type: Categorical type of deep desire (enum)
--   - primary_trigger: What triggers the pain (enum)
--   - canonical_hash: Unique fingerprint for avatar deduplication
--   - status: emerging/validated/dead lifecycle

-- Create deep_desire_type enum
DO $$ BEGIN
    CREATE TYPE genomai.deep_desire_type AS ENUM (
        'relationship_fear',    -- Fear of partner leaving/cheating
        'self_hate',           -- Self-loathing, feeling disgusted with self
        'social_rejection',    -- Fear of being laughed at, excluded
        'health_anxiety',      -- Fear of disease, death, body failure
        'financial_fear',      -- Fear of poverty, financial ruin
        'aging_fear',          -- Fear of getting old, losing youth
        'inadequacy',          -- Feeling not good enough, inferior
        'control_loss'         -- Fear of losing control over life/situation
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- Create primary_trigger enum
DO $$ BEGIN
    CREATE TYPE genomai.primary_trigger AS ENUM (
        'aging',              -- Seeing wrinkles, gray hair, physical decline
        'failure',            -- Failed diet, failed treatment, failed attempt
        'rejection',          -- Being rejected, ignored, dismissed
        'comparison',         -- Comparing to others (younger, thinner, richer)
        'health_symptom',     -- Physical symptom, pain, discomfort
        'life_event',         -- Wedding, reunion, beach vacation
        'mirror_moment',      -- Looking in mirror, seeing photo
        'partner_behavior'    -- Partner's comments, looks at others
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- Create avatar_status enum (replacing text check constraint)
DO $$ BEGIN
    CREATE TYPE genomai.avatar_status AS ENUM (
        'emerging',    -- New avatar, not yet validated by market
        'validated',   -- Has positive market signal (conversions)
        'dead'         -- Proven not to work
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- Add new columns to avatars table
ALTER TABLE genomai.avatars
ADD COLUMN IF NOT EXISTS deep_desire_type genomai.deep_desire_type,
ADD COLUMN IF NOT EXISTS primary_trigger genomai.primary_trigger,
ADD COLUMN IF NOT EXISTS canonical_hash text UNIQUE;

-- Migrate status column to new enum (if not already migrated)
DO $$
BEGIN
    -- Check if status is still text type
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'genomai'
        AND table_name = 'avatars'
        AND column_name = 'status'
        AND data_type = 'text'
    ) THEN
        -- Drop old constraint if exists
        ALTER TABLE genomai.avatars DROP CONSTRAINT IF EXISTS avatars_status_check;

        -- Create temporary column
        ALTER TABLE genomai.avatars ADD COLUMN status_new genomai.avatar_status;

        -- Migrate data (active -> validated, archived -> dead)
        UPDATE genomai.avatars SET status_new =
            CASE
                WHEN status = 'active' THEN 'validated'::genomai.avatar_status
                WHEN status = 'archived' THEN 'dead'::genomai.avatar_status
                ELSE 'emerging'::genomai.avatar_status
            END;

        -- Drop old column and rename new
        ALTER TABLE genomai.avatars DROP COLUMN status;
        ALTER TABLE genomai.avatars RENAME COLUMN status_new TO status;

        -- Set default
        ALTER TABLE genomai.avatars ALTER COLUMN status SET DEFAULT 'emerging'::genomai.avatar_status;
    END IF;
END $$;

-- Create index on canonical_hash for fast lookup
CREATE INDEX IF NOT EXISTS idx_avatars_canonical_hash
ON genomai.avatars(canonical_hash) WHERE canonical_hash IS NOT NULL;

-- Create index on deep_desire_type for analytics
CREATE INDEX IF NOT EXISTS idx_avatars_deep_desire_type
ON genomai.avatars(deep_desire_type) WHERE deep_desire_type IS NOT NULL;

-- Create index on primary_trigger for analytics
CREATE INDEX IF NOT EXISTS idx_avatars_primary_trigger
ON genomai.avatars(primary_trigger) WHERE primary_trigger IS NOT NULL;

-- Create composite index for common lookups
CREATE INDEX IF NOT EXISTS idx_avatars_desire_trigger
ON genomai.avatars(vertical, deep_desire_type, primary_trigger, awareness_level);

-- Add comment explaining canonical_hash
COMMENT ON COLUMN genomai.avatars.canonical_hash IS
'Unique fingerprint: MD5(vertical + deep_desire_type + primary_trigger + awareness_level).
Used for automatic avatar deduplication. Same combination always maps to same avatar.';

COMMENT ON COLUMN genomai.avatars.deep_desire_type IS
'Categorical deep desire from Jake CPM framework. What they REALLY want (embarrassing truth).';

COMMENT ON COLUMN genomai.avatars.primary_trigger IS
'What triggers the pain. The moment/situation that activates the deep desire.';

-- Add columns to decomposed_creatives.payload schema (documentation)
COMMENT ON TABLE genomai.decomposed_creatives IS
'Creative decomposition results from LLM analysis.
payload JSONB now includes avatar fields:
- deep_desire_type: enum matching avatars.deep_desire_type
- primary_trigger: enum matching avatars.primary_trigger
- awareness_level: already present (unaware/problem_aware/solution_aware/product_aware/most_aware)
These are used by idea_registry to find or create avatar.';

-- Function to compute canonical_hash
CREATE OR REPLACE FUNCTION genomai.compute_avatar_hash(
    p_vertical text,
    p_deep_desire_type text,
    p_primary_trigger text,
    p_awareness_level text
) RETURNS text AS $$
BEGIN
    RETURN md5(
        COALESCE(p_vertical, '') || '|' ||
        COALESCE(p_deep_desire_type, '') || '|' ||
        COALESCE(p_primary_trigger, '') || '|' ||
        COALESCE(p_awareness_level, '')
    );
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Log migration event
INSERT INTO genomai.event_log (event_type, entity_type, entity_id, payload, occurred_at)
VALUES (
    'SchemaMigration',
    'system',
    gen_random_uuid(),
    jsonb_build_object(
        'migration', '015_avatar_canonical',
        'columns_added', ARRAY['avatars.deep_desire_type', 'avatars.primary_trigger', 'avatars.canonical_hash'],
        'enums_created', ARRAY['deep_desire_type', 'primary_trigger', 'avatar_status'],
        'functions_created', ARRAY['compute_avatar_hash'],
        'description', 'Emergent avatar system - automatic avatar detection from creative decomposition'
    ),
    now()
);
