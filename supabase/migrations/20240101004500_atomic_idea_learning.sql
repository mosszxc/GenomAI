-- Migration: 045_atomic_idea_learning.sql
-- Issue: #576 - Цепочки DB операций без транзакций
-- Description: RPC functions for atomic idea creation and learning application

-- ============================================
-- Function 1: create_idea_with_link
-- ============================================
-- Creates idea and links decomposed_creative atomically.
-- If either operation fails, transaction is rolled back.

CREATE OR REPLACE FUNCTION genomai.create_idea_with_link(
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
BEGIN
    -- Insert idea
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
    RETURNING * INTO v_idea;

    -- Link decomposed_creative if provided
    IF p_decomposed_creative_id IS NOT NULL THEN
        UPDATE genomai.decomposed_creatives
        SET idea_id = p_idea_id
        WHERE id = p_decomposed_creative_id;

        IF NOT FOUND THEN
            RAISE EXCEPTION 'decomposed_creative % not found', p_decomposed_creative_id
                USING ERRCODE = 'P0002';
        END IF;
    END IF;

    RETURN jsonb_build_object(
        'idea', row_to_json(v_idea),
        'linked_decomposed_id', p_decomposed_creative_id
    );
EXCEPTION
    WHEN unique_violation THEN
        RAISE EXCEPTION 'Idea with canonical_hash % already exists', p_canonical_hash
            USING ERRCODE = '23505';
END;
$$;

GRANT EXECUTE ON FUNCTION genomai.create_idea_with_link TO service_role;

COMMENT ON FUNCTION genomai.create_idea_with_link IS
    'Atomic create idea + link decomposed_creative. Issue #576.';


-- ============================================
-- Function 2: upsert_idea_with_link
-- ============================================
-- Atomically find or create idea by canonical_hash.
-- Uses INSERT ... ON CONFLICT DO NOTHING + SELECT pattern.
-- Safe from TOCTOU race conditions.

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

    -- Link decomposed_creative if provided (for new ideas)
    IF p_decomposed_creative_id IS NOT NULL AND v_upsert_status = 'created' THEN
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
        'linked_decomposed_id', CASE WHEN v_upsert_status = 'created' THEN p_decomposed_creative_id ELSE NULL END
    );
END;
$$;

GRANT EXECUTE ON FUNCTION genomai.upsert_idea_with_link TO service_role;

COMMENT ON FUNCTION genomai.upsert_idea_with_link IS
    'Atomic upsert idea + link decomposed_creative. TOCTOU-safe. Issue #576.';


-- ============================================
-- Function 3: apply_learning_atomic
-- ============================================
-- Applies learning outcome atomically:
-- 1. INSERT idea_confidence_versions
-- 2. INSERT fatigue_state_versions
-- 3. UPDATE ideas.death_state (optional)
-- 4. UPDATE outcome_aggregates.learning_applied
-- 5. INSERT event_log

CREATE OR REPLACE FUNCTION genomai.apply_learning_atomic(
    p_idea_id UUID,
    p_outcome_id UUID,
    -- Confidence params
    p_new_confidence NUMERIC,
    p_confidence_version INT,
    p_old_confidence NUMERIC,
    p_delta NUMERIC,
    -- Fatigue params
    p_new_fatigue NUMERIC,
    p_fatigue_version INT,
    -- Death state (optional)
    p_death_state TEXT DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_confidence_result RECORD;
    v_fatigue_result RECORD;
    v_event_payload JSONB;
BEGIN
    -- 1. Insert confidence version
    INSERT INTO genomai.idea_confidence_versions (
        idea_id,
        confidence_value,
        version,
        source_outcome_id,
        change_reason,
        created_at
    ) VALUES (
        p_idea_id,
        p_new_confidence,
        p_confidence_version,
        p_outcome_id,
        'learning_applied',
        NOW()
    )
    RETURNING * INTO v_confidence_result;

    -- 2. Insert fatigue version
    INSERT INTO genomai.fatigue_state_versions (
        idea_id,
        fatigue_value,
        version,
        source_outcome_id,
        created_at
    ) VALUES (
        p_idea_id,
        p_new_fatigue,
        p_fatigue_version,
        p_outcome_id,
        NOW()
    )
    RETURNING * INTO v_fatigue_result;

    -- 3. Update death_state if provided
    IF p_death_state IS NOT NULL THEN
        UPDATE genomai.ideas
        SET death_state = p_death_state
        WHERE id = p_idea_id;
    END IF;

    -- 4. Mark outcome as processed
    UPDATE genomai.outcome_aggregates
    SET learning_applied = TRUE
    WHERE id = p_outcome_id;

    -- 5. Emit learning event
    v_event_payload := jsonb_build_object(
        'outcome_id', p_outcome_id,
        'old_confidence', p_old_confidence,
        'new_confidence', p_new_confidence,
        'delta', p_delta
    );

    IF p_death_state IS NOT NULL THEN
        v_event_payload := v_event_payload || jsonb_build_object('death_state', p_death_state);
    END IF;

    INSERT INTO genomai.event_log (
        event_type,
        entity_type,
        entity_id,
        payload,
        created_at
    ) VALUES (
        'learning.applied',
        'idea',
        p_idea_id,
        v_event_payload,
        NOW()
    );

    RETURN jsonb_build_object(
        'idea_id', p_idea_id,
        'outcome_id', p_outcome_id,
        'confidence', row_to_json(v_confidence_result),
        'fatigue', row_to_json(v_fatigue_result),
        'death_state', p_death_state
    );
EXCEPTION
    WHEN unique_violation THEN
        -- Idempotency: outcome already processed
        RAISE EXCEPTION 'Outcome % already processed for idea %', p_outcome_id, p_idea_id
            USING ERRCODE = '23505';
END;
$$;

GRANT EXECUTE ON FUNCTION genomai.apply_learning_atomic TO service_role;

COMMENT ON FUNCTION genomai.apply_learning_atomic IS
    'Atomic learning application: confidence + fatigue + death_state + mark processed + event. Issue #576.';


-- ============================================
-- Verification
-- ============================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = 'genomai'
        AND p.proname = 'create_idea_with_link'
    ) THEN
        RAISE EXCEPTION 'Function create_idea_with_link was not created';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = 'genomai'
        AND p.proname = 'upsert_idea_with_link'
    ) THEN
        RAISE EXCEPTION 'Function upsert_idea_with_link was not created';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = 'genomai'
        AND p.proname = 'apply_learning_atomic'
    ) THEN
        RAISE EXCEPTION 'Function apply_learning_atomic was not created';
    END IF;

    RAISE NOTICE 'Migration 045: atomic_idea_learning functions created successfully';
END $$;
