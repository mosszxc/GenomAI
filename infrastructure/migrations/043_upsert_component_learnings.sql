-- Migration: 043_upsert_component_learnings
-- Purpose: Add atomic upsert function for component_learnings to fix TOCTOU race condition
-- Issue: #546

-- Function to atomically upsert a batch of component learnings
-- Uses INSERT ... ON CONFLICT DO UPDATE to avoid race conditions
CREATE OR REPLACE FUNCTION genomai.upsert_component_learnings_batch(
    p_updates JSONB
)
RETURNS TABLE (
    inserted INT,
    updated INT
) AS $$
DECLARE
    v_inserted INT := 0;
    v_updated INT := 0;
    v_update JSONB;
    v_result RECORD;
BEGIN
    -- Process each update in the batch
    FOR v_update IN SELECT * FROM jsonb_array_elements(p_updates)
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

        -- xmax = 0 means INSERT, otherwise UPDATE
        IF v_result.is_insert THEN
            v_inserted := v_inserted + 1;
        ELSE
            v_updated := v_updated + 1;
        END IF;
    END LOOP;

    RETURN QUERY SELECT v_inserted, v_updated;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION genomai.upsert_component_learnings_batch(JSONB) IS
'Atomically upsert batch of component learnings using ON CONFLICT DO UPDATE.
Fixes TOCTOU race condition from issue #546.';
