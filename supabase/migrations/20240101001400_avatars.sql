-- Migration 014: Avatars Table
-- Target audience profiles based on Jake's CPM framework:
-- - Surface desire: what they say they want
-- - Deep desire: what they really want (embarrassing truth)
-- - Experiences: traumatic moments that resonate
-- - Beliefs: what they believe about their problem
-- - Behaviors: what they keep doing
-- - Awareness level: Eugene Schwartz's 5 levels

-- Create avatars table
CREATE TABLE IF NOT EXISTS genomai.avatars (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Identity
    name text NOT NULL,
    vertical text NOT NULL,
    geo text,

    -- Desire structure (Jake's framework)
    surface_desire text NOT NULL,
    deep_desire text NOT NULL,

    -- Psychological profile
    experiences text[] DEFAULT '{}',
    beliefs text[] DEFAULT '{}',
    behaviors text[] DEFAULT '{}',

    -- Awareness level (Eugene Schwartz)
    awareness_level text CHECK (awareness_level IN (
        'unaware',
        'problem_aware',
        'solution_aware',
        'product_aware',
        'most_aware'
    )),

    -- Metadata
    status text DEFAULT 'active' CHECK (status IN ('active', 'archived')),
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);

-- Add comment
COMMENT ON TABLE genomai.avatars IS
'Target audience profiles for creative targeting.
Based on Jake''s CPM framework: surface_desire (what they say), deep_desire (embarrassing truth),
experiences (traumatic moments), beliefs (what they think), behaviors (what they do).
Awareness levels from Eugene Schwartz: unaware -> problem_aware -> solution_aware -> product_aware -> most_aware.';

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_avatars_vertical ON genomai.avatars(vertical);
CREATE INDEX IF NOT EXISTS idx_avatars_geo ON genomai.avatars(geo) WHERE geo IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_avatars_awareness ON genomai.avatars(awareness_level);
CREATE INDEX IF NOT EXISTS idx_avatars_status ON genomai.avatars(status);

-- Add avatar_id to ideas table (optional link)
ALTER TABLE genomai.ideas
ADD COLUMN IF NOT EXISTS avatar_id uuid REFERENCES genomai.avatars(id);

-- Create index for avatar-idea relationship
CREATE INDEX IF NOT EXISTS idx_ideas_avatar ON genomai.ideas(avatar_id) WHERE avatar_id IS NOT NULL;

-- Create avatar_learnings table for tracking avatar-level performance
CREATE TABLE IF NOT EXISTS genomai.avatar_learnings (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    avatar_id uuid NOT NULL REFERENCES genomai.avatars(id),

    -- Performance metrics
    sample_size integer DEFAULT 0,
    win_count integer DEFAULT 0,
    loss_count integer DEFAULT 0,
    total_spend numeric(12,2) DEFAULT 0,
    total_revenue numeric(12,2) DEFAULT 0,

    -- Computed metrics
    win_rate numeric(5,4) GENERATED ALWAYS AS (
        CASE WHEN sample_size > 0 THEN win_count::numeric / sample_size ELSE 0 END
    ) STORED,
    avg_roi numeric(8,4) GENERATED ALWAYS AS (
        CASE WHEN total_spend > 0 THEN (total_revenue - total_spend) / total_spend ELSE 0 END
    ) STORED,

    -- Time window
    period_start date NOT NULL,
    period_end date NOT NULL,

    -- Metadata
    created_at timestamp with time zone DEFAULT now(),

    -- Prevent duplicates
    UNIQUE (avatar_id, period_start, period_end)
);

-- Add comment
COMMENT ON TABLE genomai.avatar_learnings IS
'Aggregated performance metrics per avatar over time periods.
Tracks win_rate and avg_roi to identify which avatars convert best.';

-- Create indexes for avatar_learnings
CREATE INDEX IF NOT EXISTS idx_avatar_learnings_avatar ON genomai.avatar_learnings(avatar_id);
CREATE INDEX IF NOT EXISTS idx_avatar_learnings_period ON genomai.avatar_learnings(period_start, period_end);
CREATE INDEX IF NOT EXISTS idx_avatar_learnings_win_rate ON genomai.avatar_learnings(win_rate DESC);

-- Insert some example avatars based on transcripts (weight loss vertical)
INSERT INTO genomai.avatars (
    name, vertical, geo,
    surface_desire, deep_desire,
    experiences, beliefs, behaviors,
    awareness_level
) VALUES
(
    'Aging Woman - Relationship Fear',
    'weight_loss',
    NULL,
    'I want to lose the wrinkles/age on my face',
    'I''m afraid my husband will leave me for a woman who looks younger',
    ARRAY[
        'Was mistaken for a grandma at daughter''s wedding',
        'Caught husband looking at a younger woman',
        'Felt invisible at a party'
    ],
    ARRAY[
        'I am stuck this way until I die',
        'No product can really help me',
        'Younger women have an unfair advantage'
    ],
    ARRAY[
        'Keep buying name brand creams in hopes for a change',
        'Research different brands and prescriptions every day',
        'Avoid mirrors and photos'
    ],
    'solution_aware'
),
(
    'Frustrated Dieter - Failed Solutions',
    'weight_loss',
    NULL,
    'I want to lose weight and feel healthy',
    'I hate myself for being weak and unable to stick to diets',
    ARRAY[
        'Tried every diet and regained all weight plus more',
        'Partner made a comment about my body',
        'Couldn''t fit into clothes at a store'
    ],
    ARRAY[
        'My metabolism is broken',
        'I lack willpower that others have',
        'Nothing will ever work for me'
    ],
    ARRAY[
        'Start new diets every Monday',
        'Buy diet books and courses but never finish',
        'Weigh myself obsessively'
    ],
    'solution_aware'
),
(
    'Teen Acne Sufferer - Social Shame',
    'skincare',
    NULL,
    'I want to get rid of blackheads and acne',
    'I''m terrified of being laughed at and rejected',
    ARRAY[
        'Someone pointed out pimple in front of whole class',
        'Crush looked at my skin and walked away',
        'Avoided photos at events'
    ],
    ARRAY[
        'I will never have clear skin like others',
        'Everyone is staring at my face',
        'I''m disgusting'
    ],
    ARRAY[
        'Pop pimples even though it makes it worse',
        'Watch skincare videos for hours',
        'Wear heavy makeup to hide skin'
    ],
    'problem_aware'
);

-- Log migration event
INSERT INTO genomai.event_log (event_type, entity_type, entity_id, payload, occurred_at)
VALUES (
    'SchemaMigration',
    'system',
    gen_random_uuid(),
    jsonb_build_object(
        'migration', '014_avatars',
        'tables_created', ARRAY['avatars', 'avatar_learnings'],
        'columns_added', ARRAY['ideas.avatar_id'],
        'description', 'Added avatar system for target audience profiling'
    ),
    now()
);
