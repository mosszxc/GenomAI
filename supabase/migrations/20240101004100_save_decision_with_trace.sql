-- Migration: 041_save_decision_with_trace.sql
-- Issue: #476 - Decision + Trace сохраняются не транзакционно
-- Description: RPC function for atomic save of decision with trace

-- ============================================
-- Function: save_decision_with_trace
-- ============================================
-- Saves Decision and Decision Trace atomically in a single transaction.
-- If either insert fails, the entire transaction is rolled back.

CREATE OR REPLACE FUNCTION genomai.save_decision_with_trace(
    p_decision_id UUID,
    p_idea_id UUID,
    p_decision TEXT,
    p_decision_epoch INT,
    p_decision_created_at TIMESTAMPTZ,
    p_trace_id UUID,
    p_trace_checks JSONB,
    p_trace_result TEXT,
    p_trace_created_at TIMESTAMPTZ
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_decision_result RECORD;
    v_trace_result RECORD;
BEGIN
    -- Insert Decision
    INSERT INTO genomai.decisions (
        id,
        idea_id,
        decision,
        decision_epoch,
        created_at
    ) VALUES (
        p_decision_id,
        p_idea_id,
        p_decision,
        p_decision_epoch,
        p_decision_created_at
    )
    RETURNING * INTO v_decision_result;

    -- Insert Decision Trace
    INSERT INTO genomai.decision_traces (
        id,
        decision_id,
        checks,
        result,
        created_at
    ) VALUES (
        p_trace_id,
        p_decision_id,
        p_trace_checks,
        p_trace_result,
        p_trace_created_at
    )
    RETURNING * INTO v_trace_result;

    -- Return both results
    RETURN jsonb_build_object(
        'decision', row_to_json(v_decision_result),
        'trace', row_to_json(v_trace_result)
    );
EXCEPTION
    WHEN unique_violation THEN
        -- Handle duplicate decision (idempotency case)
        RAISE EXCEPTION 'Decision already exists for idea_id=% epoch=%', p_idea_id, p_decision_epoch
            USING ERRCODE = '23505';
    WHEN OTHERS THEN
        -- Re-raise with context
        RAISE;
END;
$$;

-- Grant execute to authenticated users (service role)
GRANT EXECUTE ON FUNCTION genomai.save_decision_with_trace TO service_role;

-- Comment
COMMENT ON FUNCTION genomai.save_decision_with_trace IS
    'Atomic save of Decision + Decision Trace. Ensures both records are saved together or neither. Issue #476.';

-- ============================================
-- Verification
-- ============================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = 'genomai'
        AND p.proname = 'save_decision_with_trace'
    ) THEN
        RAISE EXCEPTION 'Function save_decision_with_trace was not created';
    END IF;

    RAISE NOTICE 'Migration 041: save_decision_with_trace function created successfully';
END $$;
