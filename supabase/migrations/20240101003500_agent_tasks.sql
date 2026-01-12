-- Migration: 035_agent_tasks.sql
-- Description: Multi-Agent Orchestration Phase 2 - Centralized task queue
-- Issue: #350

-- Create agent_tasks table for centralized task coordination
CREATE TABLE IF NOT EXISTS genomai.agent_tasks (
    id SERIAL PRIMARY KEY,
    issue_number INT NOT NULL UNIQUE,
    issue_title TEXT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'claimed', 'completed', 'abandoned')),
    claimed_by TEXT,
    claimed_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    last_heartbeat TIMESTAMPTZ,
    priority INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for quick lookup of pending tasks by priority
CREATE INDEX IF NOT EXISTS idx_agent_tasks_pending_priority
ON genomai.agent_tasks (priority DESC, created_at ASC)
WHERE status = 'pending';

-- Index for orphan detection (claimed but stale heartbeat)
CREATE INDEX IF NOT EXISTS idx_agent_tasks_stale_heartbeat
ON genomai.agent_tasks (last_heartbeat)
WHERE status = 'claimed';

-- Trigger to update updated_at on changes
CREATE OR REPLACE FUNCTION genomai.update_agent_tasks_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_agent_tasks_updated_at ON genomai.agent_tasks;
CREATE TRIGGER trigger_agent_tasks_updated_at
    BEFORE UPDATE ON genomai.agent_tasks
    FOR EACH ROW
    EXECUTE FUNCTION genomai.update_agent_tasks_updated_at();

-- Function for atomic claim (returns true if claim succeeded)
CREATE OR REPLACE FUNCTION genomai.claim_agent_task(
    p_issue_number INT,
    p_agent_id TEXT
) RETURNS BOOLEAN AS $$
DECLARE
    v_count INT;
BEGIN
    -- Attempt atomic claim using UPDATE with WHERE conditions
    UPDATE genomai.agent_tasks
    SET
        status = 'claimed',
        claimed_by = p_agent_id,
        claimed_at = NOW(),
        last_heartbeat = NOW()
    WHERE
        issue_number = p_issue_number
        AND status = 'pending';

    GET DIAGNOSTICS v_count = ROW_COUNT;
    RETURN v_count > 0;
END;
$$ LANGUAGE plpgsql;

-- Function for heartbeat update
CREATE OR REPLACE FUNCTION genomai.heartbeat_agent_task(
    p_issue_number INT,
    p_agent_id TEXT
) RETURNS BOOLEAN AS $$
DECLARE
    v_count INT;
BEGIN
    UPDATE genomai.agent_tasks
    SET last_heartbeat = NOW()
    WHERE
        issue_number = p_issue_number
        AND claimed_by = p_agent_id
        AND status = 'claimed';

    GET DIAGNOSTICS v_count = ROW_COUNT;
    RETURN v_count > 0;
END;
$$ LANGUAGE plpgsql;

-- Function to complete a task
CREATE OR REPLACE FUNCTION genomai.complete_agent_task(
    p_issue_number INT,
    p_agent_id TEXT
) RETURNS BOOLEAN AS $$
DECLARE
    v_count INT;
BEGIN
    UPDATE genomai.agent_tasks
    SET
        status = 'completed',
        completed_at = NOW()
    WHERE
        issue_number = p_issue_number
        AND claimed_by = p_agent_id
        AND status = 'claimed';

    GET DIAGNOSTICS v_count = ROW_COUNT;
    RETURN v_count > 0;
END;
$$ LANGUAGE plpgsql;

-- Function to release orphaned tasks (no heartbeat for 10+ minutes)
CREATE OR REPLACE FUNCTION genomai.release_orphaned_tasks(
    p_timeout_minutes INT DEFAULT 10
) RETURNS INT AS $$
DECLARE
    v_count INT;
BEGIN
    UPDATE genomai.agent_tasks
    SET
        status = 'abandoned',
        claimed_by = NULL,
        claimed_at = NULL,
        last_heartbeat = NULL
    WHERE
        status = 'claimed'
        AND last_heartbeat < NOW() - (p_timeout_minutes || ' minutes')::INTERVAL;

    GET DIAGNOSTICS v_count = ROW_COUNT;
    RETURN v_count;
END;
$$ LANGUAGE plpgsql;

-- Comment for documentation
COMMENT ON TABLE genomai.agent_tasks IS 'Centralized task queue for multi-agent coordination (Phase 2)';
COMMENT ON FUNCTION genomai.claim_agent_task IS 'Atomically claim a pending task. Returns true on success.';
COMMENT ON FUNCTION genomai.heartbeat_agent_task IS 'Update heartbeat for a claimed task. Returns true if still owned.';
COMMENT ON FUNCTION genomai.complete_agent_task IS 'Mark a claimed task as completed. Returns true on success.';
COMMENT ON FUNCTION genomai.release_orphaned_tasks IS 'Release tasks with stale heartbeats (default: 10 min timeout).';
