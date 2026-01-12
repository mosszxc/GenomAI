-- Migration: 032_component_learning_snapshots
-- Issue: #294 - Drift Detection

CREATE TABLE IF NOT EXISTS genomai.component_learning_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    snapshot_date DATE NOT NULL,
    component_type TEXT NOT NULL,
    component_value TEXT NOT NULL,
    geo TEXT DEFAULT 'GLOBAL',
    avatar_id UUID,

    sample_size INTEGER DEFAULT 0,
    win_count INTEGER DEFAULT 0,
    loss_count INTEGER DEFAULT 0,
    total_spend NUMERIC(12,2) DEFAULT 0,
    total_revenue NUMERIC(12,2) DEFAULT 0,
    win_rate NUMERIC(5,4),
    avg_roi NUMERIC(8,4),

    created_at TIMESTAMPTZ DEFAULT now()
);

-- Unique index with COALESCE for NULL handling
CREATE UNIQUE INDEX IF NOT EXISTS idx_cls_unique_snapshot
ON genomai.component_learning_snapshots(
    snapshot_date,
    component_type,
    component_value,
    COALESCE(geo, 'GLOBAL'),
    COALESCE(avatar_id, '00000000-0000-0000-0000-000000000000'::uuid)
);

CREATE INDEX IF NOT EXISTS idx_cls_date_type
ON genomai.component_learning_snapshots(snapshot_date, component_type);

CREATE INDEX IF NOT EXISTS idx_cls_component
ON genomai.component_learning_snapshots(component_type, component_value);

-- Function to create daily snapshot
CREATE OR REPLACE FUNCTION genomai.create_component_learning_snapshot()
RETURNS INTEGER AS $$
DECLARE
    snapshot_count INTEGER;
BEGIN
    INSERT INTO genomai.component_learning_snapshots (
        snapshot_date,
        component_type,
        component_value,
        geo,
        avatar_id,
        sample_size,
        win_count,
        loss_count,
        total_spend,
        total_revenue,
        win_rate,
        avg_roi
    )
    SELECT
        CURRENT_DATE,
        component_type,
        component_value,
        COALESCE(geo, 'GLOBAL'),
        avatar_id,
        sample_size,
        win_count,
        loss_count,
        total_spend,
        total_revenue,
        CASE WHEN sample_size > 0 THEN win_count::numeric / sample_size ELSE 0 END,
        CASE WHEN total_spend > 0 THEN (total_revenue - total_spend) / total_spend ELSE 0 END
    FROM genomai.component_learnings
    WHERE sample_size > 0
    ON CONFLICT (
        snapshot_date,
        component_type,
        component_value,
        COALESCE(geo, 'GLOBAL'),
        COALESCE(avatar_id, '00000000-0000-0000-0000-000000000000'::uuid)
    )
    DO UPDATE SET
        sample_size = EXCLUDED.sample_size,
        win_count = EXCLUDED.win_count,
        loss_count = EXCLUDED.loss_count,
        total_spend = EXCLUDED.total_spend,
        total_revenue = EXCLUDED.total_revenue,
        win_rate = EXCLUDED.win_rate,
        avg_roi = EXCLUDED.avg_roi;

    GET DIAGNOSTICS snapshot_count = ROW_COUNT;
    RETURN snapshot_count;
END;
$$ LANGUAGE plpgsql;

SELECT genomai.create_component_learning_snapshot();

COMMENT ON TABLE genomai.component_learning_snapshots IS
'Daily snapshots of component_learnings for drift detection. Issue #294.';
