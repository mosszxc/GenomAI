-- Migration 013: Canonical Schema v2
-- Extends decomposed_creatives.payload with copywriting psychology fields
-- Based on analysis of expert transcripts (Jake, John Benson)
--
-- New fields (all optional, stored in JSONB payload):
-- - UMP/UMS: ump_present, ump_type, ums_present, ums_type
-- - Paradigm Shift: paradigm_shift_present, paradigm_shift_type
-- - Specificity: specificity_level, specificity_markers[]
-- - Hook: hook_mechanism, hook_stopping_power
-- - Proof: proof_type, proof_source
-- - Story: story_type, story_bridge_present
-- - Desire: desire_level, emotional_trigger
-- - Social Proof: social_proof_pattern, proof_progression
-- - CTA: cta_style, risk_reversal_type
-- - Focus: focus_score, idea_count, emotion_count
--
-- No structural changes needed - payload is already JSONB
-- This migration adds documentation and validation function

-- Add comment documenting schema v2
COMMENT ON TABLE genomai.decomposed_creatives IS
'Decomposed creative components.
Schema v1 (14 required fields): angle_type, core_belief, promise_type, emotion_primary, emotion_intensity, message_structure, opening_type, state_before, state_after, context_frame, source_type, risk_level, horizon, schema_version.
Schema v2 (14 required + 22 optional): Adds UMP/UMS, paradigm_shift, specificity, hook, proof, story, desire, social_proof, cta, focus fields.
See infrastructure/schemas/idea_schema_v2.json for full specification.';

-- Create validation function for schema v2
CREATE OR REPLACE FUNCTION genomai.validate_schema_v2(payload jsonb)
RETURNS boolean AS $$
DECLARE
    required_fields text[] := ARRAY[
        'angle_type', 'core_belief', 'promise_type', 'emotion_primary',
        'emotion_intensity', 'message_structure', 'opening_type',
        'state_before', 'state_after', 'context_frame', 'source_type',
        'risk_level', 'horizon', 'schema_version'
    ];
    field text;
BEGIN
    -- Check all required fields present
    FOREACH field IN ARRAY required_fields LOOP
        IF NOT (payload ? field) THEN
            RAISE NOTICE 'Missing required field: %', field;
            RETURN false;
        END IF;
    END LOOP;

    -- Validate schema_version is v1 or v2
    IF payload->>'schema_version' NOT IN ('v1', 'v2') THEN
        RAISE NOTICE 'Invalid schema_version: %', payload->>'schema_version';
        RETURN false;
    END IF;

    RETURN true;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Add index for schema_version queries
CREATE INDEX IF NOT EXISTS idx_decomposed_creatives_schema_version
ON genomai.decomposed_creatives ((payload->>'schema_version'));

-- Add index for UMP presence (common learning query)
CREATE INDEX IF NOT EXISTS idx_decomposed_creatives_ump_present
ON genomai.decomposed_creatives ((payload->>'ump_present'))
WHERE payload->>'schema_version' = 'v2';

-- Add index for specificity level (common learning query)
CREATE INDEX IF NOT EXISTS idx_decomposed_creatives_specificity
ON genomai.decomposed_creatives ((payload->>'specificity_level'))
WHERE payload->>'schema_version' = 'v2';

-- Add index for hook stopping power (performance analysis)
CREATE INDEX IF NOT EXISTS idx_decomposed_creatives_hook_power
ON genomai.decomposed_creatives ((payload->>'hook_stopping_power'))
WHERE payload->>'schema_version' = 'v2';

-- Log migration event
INSERT INTO genomai.event_log (event_type, entity_type, entity_id, payload, occurred_at)
VALUES (
    'SchemaMigration',
    'system',
    gen_random_uuid(),
    jsonb_build_object(
        'migration', '013_canonical_schema_v2',
        'from_version', 'v1',
        'to_version', 'v2',
        'new_fields_count', 22,
        'description', 'Extended canonical schema with copywriting psychology fields'
    ),
    now()
);
