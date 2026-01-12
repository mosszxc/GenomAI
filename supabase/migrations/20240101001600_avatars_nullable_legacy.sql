-- Migration 016: Make legacy avatar fields nullable
-- surface_desire and deep_desire are replaced by deep_desire_type enum
-- These text fields are now optional for backward compatibility

ALTER TABLE genomai.avatars
    ALTER COLUMN surface_desire DROP NOT NULL,
    ALTER COLUMN deep_desire DROP NOT NULL;

COMMENT ON COLUMN genomai.avatars.surface_desire IS
'Legacy: Free-text surface desire. Replaced by deep_desire_type enum for emergent avatars.';

COMMENT ON COLUMN genomai.avatars.deep_desire IS
'Legacy: Free-text deep desire. Replaced by deep_desire_type enum for emergent avatars.';

-- Log migration
INSERT INTO genomai.event_log (event_type, entity_type, entity_id, payload, occurred_at)
VALUES (
    'SchemaMigration',
    'system',
    gen_random_uuid(),
    jsonb_build_object(
        'migration', '016_avatars_nullable_legacy',
        'changes', 'Made surface_desire and deep_desire nullable for emergent avatar system'
    ),
    now()
);
