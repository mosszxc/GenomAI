-- Migration: 046_apply_learning_complete_atomic.sql
-- Issue: #732 - component/premise learning не атомарны с core learning
-- Description: Atomic RPC that combines core learning + component learning + premise learning

-- ============================================
-- Function: apply_learning_complete_atomic
-- ============================================
-- Extends apply_learning_atomic to include:
-- 1. Core learning (confidence, fatigue, death_state, mark processed, event)
-- 2. Component learnings batch upsert
-- 3. Premise learnings upsert
-- All in single transaction - either all succeed or all rollback.

CREATE OR REPLACE FUNCTION genomai.apply_learning_complete_atomic(
    -- Core learning params (same as apply_learning_atomic)
    p_idea_id UUID,
    p_outcome_id UUID,
    p_new_confidence NUMERIC,
    p_confidence_version INT,
    p_old_confidence NUMERIC,
    p_delta NUMERIC,
    p_new_fatigue NUMERIC,
    p_fatigue_version INT,
    p_death_state TEXT DEFAULT NULL,
    -- Component learnings (JSONB array)
    p_component_updates JSONB DEFAULT NULL,
    -- Premise learnings (JSONB array, supports global + per-avatar)
    p_premise_updates JSONB DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_confidence_result RECORD;
    v_fatigue_result RECORD;
    v_event_payload JSONB;
    v_component_inserted INT := 0;
    v_component_updated INT := 0;
    v_premise_inserted INT := 0;
    v_premise_updated INT := 0;
    v_update JSONB;
    v_result RECORD;
BEGIN
    -- =====================
    -- 1. Core Learning (from apply_learning_atomic)
    -- =====================

    -- 1.1 Insert confidence version
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

    -- 1.2 Insert fatigue version
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

    -- 1.3 Update death_state if provided
    IF p_death_state IS NOT NULL THEN
        UPDATE genomai.ideas
        SET death_state = p_death_state
        WHERE id = p_idea_id;
    END IF;

    -- 1.4 Mark outcome as processed
    UPDATE genomai.outcome_aggregates
    SET learning_applied = TRUE
    WHERE id = p_outcome_id;

    -- =====================
    -- 2. Component Learnings
    -- =====================
    IF p_component_updates IS NOT NULL AND jsonb_array_length(p_component_updates) > 0 THEN
        FOR v_update IN SELECT * FROM jsonb_array_elements(p_component_updates)
        LOOP
            INSERT INTO genomai.component_learnings (
                component_type,
                component_value,
                geo,
                avatar_id,
                sample_size,
                win_count,
                loss_count,
                total_spend,
                total_revenue
            ) VALUES (
                v_update->>'component_type',
                v_update->>'component_value',
                NULLIF(v_update->>'geo', ''),
                CASE
                    WHEN v_update->>'avatar_id' IS NOT NULL AND v_update->>'avatar_id' != ''
                    THEN (v_update->>'avatar_id')::UUID
                    ELSE NULL
                END,
                COALESCE((v_update->>'sample_size')::INT, 1),
                COALESCE((v_update->>'win_count')::INT, 0),
                COALESCE((v_update->>'loss_count')::INT, 0),
                COALESCE((v_update->>'total_spend')::NUMERIC, 0),
                COALESCE((v_update->>'total_revenue')::NUMERIC, 0)
            )
            ON CONFLICT (component_type, component_value, geo, avatar_id)
            DO UPDATE SET
                sample_size = component_learnings.sample_size + COALESCE((v_update->>'sample_size')::INT, 1),
                win_count = component_learnings.win_count + COALESCE((v_update->>'win_count')::INT, 0),
                loss_count = component_learnings.loss_count + COALESCE((v_update->>'loss_count')::INT, 0),
                total_spend = component_learnings.total_spend + COALESCE((v_update->>'total_spend')::NUMERIC, 0),
                total_revenue = component_learnings.total_revenue + COALESCE((v_update->>'total_revenue')::NUMERIC, 0),
                updated_at = now()
            RETURNING (xmax = 0) AS is_insert INTO v_result;

            IF v_result.is_insert THEN
                v_component_inserted := v_component_inserted + 1;
            ELSE
                v_component_updated := v_component_updated + 1;
            END IF;
        END LOOP;
    END IF;

    -- =====================
    -- 3. Premise Learnings
    -- =====================
    IF p_premise_updates IS NOT NULL AND jsonb_array_length(p_premise_updates) > 0 THEN
        FOR v_update IN SELECT * FROM jsonb_array_elements(p_premise_updates)
        LOOP
            INSERT INTO genomai.premise_learnings (
                premise_id,
                premise_type,
                geo,
                avatar_id,
                sample_size,
                win_count,
                loss_count,
                total_spend,
                total_revenue
            ) VALUES (
                (v_update->>'premise_id')::UUID,
                v_update->>'premise_type',
                NULLIF(v_update->>'geo', ''),
                CASE
                    WHEN v_update->>'avatar_id' IS NOT NULL AND v_update->>'avatar_id' != ''
                    THEN (v_update->>'avatar_id')::UUID
                    ELSE NULL
                END,
                COALESCE((v_update->>'sample_size')::INT, 1),
                COALESCE((v_update->>'win_count')::INT, 0),
                COALESCE((v_update->>'loss_count')::INT, 0),
                COALESCE((v_update->>'total_spend')::NUMERIC, 0),
                COALESCE((v_update->>'total_revenue')::NUMERIC, 0)
            )
            ON CONFLICT (premise_id, geo, avatar_id)
            DO UPDATE SET
                sample_size = premise_learnings.sample_size + COALESCE((v_update->>'sample_size')::INT, 1),
                win_count = premise_learnings.win_count + COALESCE((v_update->>'win_count')::INT, 0),
                loss_count = premise_learnings.loss_count + COALESCE((v_update->>'loss_count')::INT, 0),
                total_spend = premise_learnings.total_spend + COALESCE((v_update->>'total_spend')::NUMERIC, 0),
                total_revenue = premise_learnings.total_revenue + COALESCE((v_update->>'total_revenue')::NUMERIC, 0),
                updated_at = now()
            RETURNING (xmax = 0) AS is_insert INTO v_result;

            IF v_result.is_insert THEN
                v_premise_inserted := v_premise_inserted + 1;
            ELSE
                v_premise_updated := v_premise_updated + 1;
            END IF;
        END LOOP;
    END IF;

    -- =====================
    -- 4. Emit Event
    -- =====================
    v_event_payload := jsonb_build_object(
        'outcome_id', p_outcome_id,
        'old_confidence', p_old_confidence,
        'new_confidence', p_new_confidence,
        'delta', p_delta,
        'component_learnings', jsonb_build_object(
            'inserted', v_component_inserted,
            'updated', v_component_updated
        ),
        'premise_learnings', jsonb_build_object(
            'inserted', v_premise_inserted,
            'updated', v_premise_updated
        )
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
        'learning.complete_applied',
        'idea',
        p_idea_id,
        v_event_payload,
        NOW()
    );

    -- =====================
    -- 5. Return Result
    -- =====================
    RETURN jsonb_build_object(
        'idea_id', p_idea_id,
        'outcome_id', p_outcome_id,
        'confidence', row_to_json(v_confidence_result),
        'fatigue', row_to_json(v_fatigue_result),
        'death_state', p_death_state,
        'component_learnings', jsonb_build_object(
            'inserted', v_component_inserted,
            'updated', v_component_updated
        ),
        'premise_learnings', jsonb_build_object(
            'inserted', v_premise_inserted,
            'updated', v_premise_updated
        )
    );

EXCEPTION
    WHEN unique_violation THEN
        -- Idempotency: outcome already processed
        RAISE EXCEPTION 'Outcome % already processed for idea %', p_outcome_id, p_idea_id
            USING ERRCODE = '23505';
END;
$$;

GRANT EXECUTE ON FUNCTION genomai.apply_learning_complete_atomic TO service_role;

COMMENT ON FUNCTION genomai.apply_learning_complete_atomic IS
'Atomic learning application: core (confidence + fatigue + death_state) + component learnings + premise learnings.
All operations in single transaction. Issue #732.';


-- ============================================
-- Monitoring: View for detecting sync issues
-- ============================================

CREATE OR REPLACE VIEW genomai.learning_sync_status AS
SELECT
    oa.id AS outcome_id,
    oa.idea_id,
    oa.creative_id,
    oa.learning_applied,
    oa.updated_at AS outcome_updated_at,
    -- Check if confidence version exists
    EXISTS (
        SELECT 1 FROM genomai.idea_confidence_versions icv
        WHERE icv.source_outcome_id = oa.id
    ) AS has_confidence_version,
    -- Check if any component learnings updated after outcome
    -- (This is approximate - we can't know exact component updates per outcome)
    oa.learning_applied AND NOT EXISTS (
        SELECT 1 FROM genomai.event_log el
        WHERE el.entity_id = oa.idea_id
        AND el.event_type = 'learning.complete_applied'
        AND el.payload->>'outcome_id' = oa.id::text
    ) AS potentially_out_of_sync
FROM genomai.outcome_aggregates oa
WHERE oa.learning_applied = TRUE;

COMMENT ON VIEW genomai.learning_sync_status IS
'View to detect potential sync issues between core learning and component/premise learning.
Issue #732.';


-- ============================================
-- Verification
-- ============================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = 'genomai'
        AND p.proname = 'apply_learning_complete_atomic'
    ) THEN
        RAISE EXCEPTION 'Function apply_learning_complete_atomic was not created';
    END IF;

    RAISE NOTICE 'Migration 046: apply_learning_complete_atomic created successfully';
END $$;
