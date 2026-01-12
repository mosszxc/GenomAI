-- Hygiene Reports Table
-- Stores health check and maintenance reports for trend analysis

CREATE TABLE IF NOT EXISTS genomai.hygiene_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Report type: maintenance (6h) or health_check (3h)
    report_type TEXT NOT NULL CHECK (report_type IN ('maintenance', 'health_check')),

    -- Health metrics
    health_score NUMERIC(3,2),  -- 0.00 to 1.00
    supabase_connected BOOLEAN,
    supabase_latency_ms NUMERIC,
    temporal_connected BOOLEAN,
    temporal_latency_ms NUMERIC,

    -- Cleanup stats (for maintenance reports)
    -- {import_queue: 5, knowledge: 0, raw_metrics: 3, buyer_states: 1, staleness: 0}
    cleanup_stats JSONB,

    -- Integrity issues found
    -- [{severity: "warning", table: "decomposed_creatives", issue_type: "orphan", count: 5}]
    integrity_issues JSONB,

    -- Table row counts snapshot
    -- {creatives: 1234, ideas: 567, decisions: 890}
    table_sizes JSONB,

    -- Pending items counts
    -- {historical_import_queue: 45, knowledge_extractions: 8}
    pending_counts JSONB,

    -- Alerts sent during this run
    alerts_sent INTEGER DEFAULT 0,
    alert_details JSONB,

    -- Workflow tracking
    workflow_id TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Index for querying recent reports
CREATE INDEX IF NOT EXISTS idx_hygiene_reports_created
ON genomai.hygiene_reports(created_at DESC);

-- Index for report type filtering
CREATE INDEX IF NOT EXISTS idx_hygiene_reports_type
ON genomai.hygiene_reports(report_type, created_at DESC);

COMMENT ON TABLE genomai.hygiene_reports IS
'Hygiene system reports: health checks (3h) and maintenance runs (6h). Used for trend analysis and alerting.';
