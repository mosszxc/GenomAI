-- Migration: 021_premise_registry.sql
-- Issue: #166
-- Description: Create Premise Layer tables for narrative vehicle tracking
-- Pattern: component_learnings, 006_learning.sql

-- ============================================
-- 1. Premises Table (Registry)
-- ============================================

CREATE TABLE IF NOT EXISTS genomai.premises (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Core identity
    premise_type TEXT NOT NULL CHECK (premise_type IN (
        'method',           -- "Lemon seed method", "2-minute technique"
        'discovery',        -- "Ancient discovery", "Lab accident"
        'confession',       -- "Doctor's confession", "Industry insider"
        'secret',           -- "Hidden secret", "Suppressed information"
        'ingredient',       -- "Single ingredient", "Natural compound"
        'mechanism',        -- "Root cause", "Hidden trigger"
        'breakthrough',     -- "Scientific breakthrough", "New research"
        'transformation'    -- "Simple change", "One tweak"
    )),
    name TEXT NOT NULL,
    description TEXT,

    -- Narrative structure
    origin_story TEXT,          -- How it was "discovered"
    mechanism_claim TEXT,       -- What it claims to do

    -- Metadata
    source TEXT CHECK (source IN ('manual', 'llm_generated', 'extracted')),

    -- State
    status TEXT DEFAULT 'emerging' CHECK (status IN (
        'active',       -- Available for hypothesis generation
        'emerging',     -- New, not yet validated
        'fatigued',     -- Overused, needs rest
        'dead'          -- No longer performing
    )),

    -- Context constraints
    vertical TEXT,
    geo TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),

    -- Unique per name+vertical
    UNIQUE (name, vertical)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_premises_type ON genomai.premises(premise_type);
CREATE INDEX IF NOT EXISTS idx_premises_status ON genomai.premises(status) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_premises_vertical ON genomai.premises(vertical) WHERE vertical IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_premises_source ON genomai.premises(source);

-- Comments
COMMENT ON TABLE genomai.premises IS
'Premise Registry: Narrative vehicles for hypotheses.
Premise = the story mechanism that wraps the Idea.
Examples: "lemon seed method", "monk technique".
One Idea can be wrapped in multiple premises for testing.
Issue: #166';

COMMENT ON COLUMN genomai.premises.premise_type IS 'Category of narrative vehicle';
COMMENT ON COLUMN genomai.premises.name IS 'Human-readable premise name';
COMMENT ON COLUMN genomai.premises.origin_story IS 'How the method was discovered (narrative)';
COMMENT ON COLUMN genomai.premises.mechanism_claim IS 'What the method claims to do';

-- ============================================
-- 2. Add premise_id to hypotheses
-- ============================================

ALTER TABLE genomai.hypotheses
ADD COLUMN IF NOT EXISTS premise_id UUID REFERENCES genomai.premises(id);

CREATE INDEX IF NOT EXISTS idx_hypotheses_premise_id ON genomai.hypotheses(premise_id);

COMMENT ON COLUMN genomai.hypotheses.premise_id IS
'Optional premise used for this hypothesis. NULL = no explicit premise.';

-- ============================================
-- 3. Premise Learnings (pattern: component_learnings)
-- ============================================

CREATE TABLE IF NOT EXISTS genomai.premise_learnings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Premise identity
    premise_id UUID NOT NULL REFERENCES genomai.premises(id),
    premise_type TEXT NOT NULL,  -- Denormalized for queries

    -- Context
    geo TEXT,
    avatar_id UUID REFERENCES genomai.avatars(id),

    -- Metrics (same pattern as component_learnings)
    sample_size INT DEFAULT 0,
    win_count INT DEFAULT 0,
    loss_count INT DEFAULT 0,
    total_spend NUMERIC DEFAULT 0,
    total_revenue NUMERIC DEFAULT 0,

    -- Generated columns
    win_rate NUMERIC GENERATED ALWAYS AS (
        CASE WHEN sample_size > 0 THEN win_count::numeric / sample_size::numeric ELSE 0 END
    ) STORED,
    avg_roi NUMERIC GENERATED ALWAYS AS (
        CASE WHEN total_spend > 0 THEN (total_revenue - total_spend) / total_spend ELSE 0 END
    ) STORED,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),

    -- Unique per context
    UNIQUE (premise_id, geo, avatar_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_premise_learnings_premise_id ON genomai.premise_learnings(premise_id);
CREATE INDEX IF NOT EXISTS idx_premise_learnings_win_rate ON genomai.premise_learnings(win_rate DESC);
CREATE INDEX IF NOT EXISTS idx_premise_learnings_avatar_id ON genomai.premise_learnings(avatar_id);

-- Comments
COMMENT ON TABLE genomai.premise_learnings IS
'Aggregated performance stats per premise, by context (geo, avatar).
Same pattern as component_learnings. win_rate and avg_roi are generated columns.
Issue: #166';

-- ============================================
-- 4. Seed Initial Premises
-- ============================================

INSERT INTO genomai.premises (premise_type, name, origin_story, mechanism_claim, source, status) VALUES
    ('method', 'Метод лимонной косточки', 'Бразильские старики жевали косточки лимона', 'Растворяет отложения в суставах', 'manual', 'active'),
    ('method', 'Метод гуавы', 'Жители тропических островов', 'Очищает организм от токсинов', 'manual', 'active'),
    ('secret', 'Техника монахов', 'Тибетские монастыри, передается веками', 'Древняя мудрость для долголетия', 'manual', 'active'),
    ('method', 'Домашний метод', 'Обычная кухня, простые ингредиенты', 'Доступно каждому без врачей', 'manual', 'active'),
    ('discovery', 'Случайное открытие ученого', 'Лаборатория, побочный эффект исследования', 'Научно подтвержденный механизм', 'manual', 'active'),
    ('confession', 'Признание врача', 'Бывший врач раскрывает правду', 'То что скрывает фармацевтика', 'manual', 'active'),
    ('ingredient', 'Один ингредиент', 'Найден в природе', 'Один простой продукт решает проблему', 'manual', 'active'),
    ('mechanism', 'Скрытая причина', 'Истинный корень проблемы', 'Устраняет причину а не симптомы', 'manual', 'active')
ON CONFLICT (name, vertical) DO NOTHING;

-- ============================================
-- 5. Verification
-- ============================================

DO $$
BEGIN
    -- Verify premises table
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'genomai'
        AND table_name = 'premises'
    ) THEN
        RAISE EXCEPTION 'Table premises was not created successfully';
    END IF;

    -- Verify premise_learnings table
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'genomai'
        AND table_name = 'premise_learnings'
    ) THEN
        RAISE EXCEPTION 'Table premise_learnings was not created successfully';
    END IF;

    -- Verify hypotheses.premise_id column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'genomai'
        AND table_name = 'hypotheses'
        AND column_name = 'premise_id'
    ) THEN
        RAISE EXCEPTION 'Column hypotheses.premise_id was not created successfully';
    END IF;

    -- Verify seed data
    IF (SELECT COUNT(*) FROM genomai.premises) < 4 THEN
        RAISE EXCEPTION 'Seed premises were not inserted successfully';
    END IF;

    RAISE NOTICE 'Migration 021_premise_registry.sql completed successfully';
END $$;
