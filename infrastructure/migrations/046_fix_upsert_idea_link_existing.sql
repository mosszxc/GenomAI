-- Migration: 046_fix_upsert_idea_link_existing.sql
-- Issue: #707 - 4 из 5 decomposed_creatives не связаны с idea (idea_id = null)
-- Description: Fix RPC function to link idea_id for BOTH new AND existing ideas
--              Also retroactively fix existing orphaned records

-- ============================================
-- Problem Analysis
-- ============================================
-- The upsert_idea_with_link function only linked decomposed_creatives
-- when a NEW idea was created (v_upsert_status = 'created').
-- For existing ideas, idea_id remained NULL.
--
-- Fix: Always link decomposed_creative when provided, regardless of
-- whether the idea is new or existing.

-- ============================================
-- Step 1: Fix the RPC function
-- ============================================

CREATE OR REPLACE FUNCTION genomai.upsert_idea_with_link(
    p_idea_id UUID,
    p_canonical_hash TEXT,
    p_avatar_id UUID DEFAULT NULL,
    p_decomposed_creative_id UUID DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_idea RECORD;
    v_upsert_status TEXT;
BEGIN
    -- Try INSERT with ON CONFLICT DO NOTHING
    INSERT INTO genomai.ideas (
        id,
        canonical_hash,
        status,
        avatar_id,
        created_at
    ) VALUES (
        p_idea_id,
        p_canonical_hash,
        'active',
        p_avatar_id,
        NOW()
    )
    ON CONFLICT (canonical_hash) DO NOTHING
    RETURNING * INTO v_idea;

    IF v_idea.id IS NOT NULL THEN
        -- INSERT succeeded - new idea created
        v_upsert_status := 'created';
    ELSE
        -- Conflict - fetch existing
        SELECT * INTO v_idea
        FROM genomai.ideas
        WHERE canonical_hash = p_canonical_hash;

        v_upsert_status := 'existing';
    END IF;

    -- FIX #707: Link decomposed_creative ALWAYS when provided
    -- Previously this only happened for v_upsert_status = 'created'
    IF p_decomposed_creative_id IS NOT NULL THEN
        UPDATE genomai.decomposed_creatives
        SET idea_id = v_idea.id
        WHERE id = p_decomposed_creative_id;

        IF NOT FOUND THEN
            RAISE EXCEPTION 'decomposed_creative % not found', p_decomposed_creative_id
                USING ERRCODE = 'P0002';
        END IF;
    END IF;

    RETURN jsonb_build_object(
        'idea', row_to_json(v_idea),
        'upsert_status', v_upsert_status,
        'linked_decomposed_id', p_decomposed_creative_id
    );
END;
$$;

COMMENT ON FUNCTION genomai.upsert_idea_with_link IS
    'Atomic upsert idea + link decomposed_creative (always). TOCTOU-safe. Issues #576, #707.';


-- ============================================
-- Step 2: Retroactively fix orphaned records
-- ============================================
-- Link decomposed_creatives to ideas via canonical_hash in payload

DO $$
DECLARE
    v_fixed_count INT := 0;
    v_dc RECORD;
BEGIN
    -- Find decomposed_creatives without idea_id that have canonical_hash in payload
    FOR v_dc IN
        SELECT
            dc.id AS decomposed_id,
            dc.payload->>'canonical_hash' AS canonical_hash
        FROM genomai.decomposed_creatives dc
        WHERE dc.idea_id IS NULL
          AND dc.payload->>'canonical_hash' IS NOT NULL
    LOOP
        -- Try to find matching idea by canonical_hash
        UPDATE genomai.decomposed_creatives dc
        SET idea_id = i.id
        FROM genomai.ideas i
        WHERE dc.id = v_dc.decomposed_id
          AND i.canonical_hash = v_dc.canonical_hash;

        IF FOUND THEN
            v_fixed_count := v_fixed_count + 1;
        END IF;
    END LOOP;

    RAISE NOTICE 'Migration 046: Fixed % orphaned decomposed_creatives', v_fixed_count;
END $$;


-- ============================================
-- Verification
-- ============================================

DO $$
DECLARE
    v_orphan_count INT;
BEGIN
    -- Check remaining orphans (some may still exist if idea was never created)
    SELECT COUNT(*) INTO v_orphan_count
    FROM genomai.decomposed_creatives
    WHERE idea_id IS NULL;

    IF v_orphan_count > 0 THEN
        RAISE NOTICE 'Migration 046: % decomposed_creatives still have no idea_id (ideas may not exist)', v_orphan_count;
    ELSE
        RAISE NOTICE 'Migration 046: All decomposed_creatives are now linked to ideas';
    END IF;

    RAISE NOTICE 'Migration 046: upsert_idea_with_link fixed successfully';
END $$;
