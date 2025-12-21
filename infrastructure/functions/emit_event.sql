-- Function: emit_event
-- Purpose: Helper function for emitting events to event_log
-- Usage: SELECT emit_event('EventType', 'entity_type', 'entity_id'::uuid, '{"key": "value"}'::jsonb, 'idempotency_key');
-- Based on: EVENT_MODEL.md, API_CONTRACTS.md

-- ============================================
-- Emit Event Function
-- ============================================

CREATE OR REPLACE FUNCTION emit_event(
  p_event_type text,
  p_entity_type text DEFAULT NULL,
  p_entity_id uuid DEFAULT NULL,
  p_payload jsonb DEFAULT NULL,
  p_idempotency_key text DEFAULT NULL,
  p_occurred_at timestamp DEFAULT now()
)
RETURNS uuid
LANGUAGE plpgsql
AS $$
DECLARE
  v_event_id uuid;
BEGIN
  -- Check idempotency if key provided
  IF p_idempotency_key IS NOT NULL THEN
    SELECT id INTO v_event_id
    FROM event_log
    WHERE idempotency_key = p_idempotency_key
    LIMIT 1;
    
    IF v_event_id IS NOT NULL THEN
      -- Event already exists, return existing ID (idempotent)
      RETURN v_event_id;
    END IF;
  END IF;
  
  -- Insert new event
  INSERT INTO event_log (
    event_type,
    entity_type,
    entity_id,
    payload,
    occurred_at,
    idempotency_key
  ) VALUES (
    p_event_type,
    p_entity_type,
    p_entity_id,
    p_payload,
    p_occurred_at,
    p_idempotency_key
  )
  RETURNING id INTO v_event_id;
  
  RETURN v_event_id;
EXCEPTION
  WHEN unique_violation THEN
    -- Idempotency key conflict (race condition)
    -- Return existing event ID
    SELECT id INTO v_event_id
    FROM event_log
    WHERE idempotency_key = p_idempotency_key
    LIMIT 1;
    
    RETURN v_event_id;
  WHEN OTHERS THEN
    -- Re-raise exception
    RAISE;
END;
$$;

-- ============================================
-- Comments
-- ============================================

COMMENT ON FUNCTION emit_event IS 'Helper function for emitting events to event_log with idempotency support';
COMMENT ON FUNCTION emit_event(text, text, uuid, jsonb, text, timestamp) IS 
'Emits an event to event_log. Returns event ID. Supports idempotency via idempotency_key.';

-- ============================================
-- Usage Examples
-- ============================================

-- Example 1: Simple event
-- SELECT emit_event('CreativeReferenceReceived', 'creative', '123e4567-e89b-12d3-a456-426614174000'::uuid);

-- Example 2: Event with payload
-- SELECT emit_event(
--   'DecisionMade',
--   'decision',
--   '123e4567-e89b-12d3-a456-426614174000'::uuid,
--   '{"decision": "approve", "reason": "high_confidence"}'::jsonb
-- );

-- Example 3: Event with idempotency key
-- SELECT emit_event(
--   'DailyMetricsSnapshotCreated',
--   'creative',
--   '123e4567-e89b-12d3-a456-426614174000'::uuid,
--   '{"snapshot_date": "2025-01-01"}'::jsonb,
--   'creative:123e4567-e89b-12d3-a456-426614174000:date:2025-01-01'
-- );

