-- Migration: 036_agents_registry.sql
-- Description: Multi-Agent Orchestration Phase 3 - Agent Registry & Supervisor
-- Issue: #351

-- Create agents table for agent registration
CREATE TABLE IF NOT EXISTS genomai.agents (
    id SERIAL PRIMARY KEY,
    agent_id TEXT NOT NULL UNIQUE,
    hostname TEXT NOT NULL,
    -- Status: online (ready), busy (working on task), offline (unregistered/dead)
    status TEXT NOT NULL DEFAULT 'online' CHECK (status IN ('online', 'busy', 'offline')),
    -- Current task (if busy)
    current_task_issue INT REFERENCES genomai.agent_tasks(issue_number),
    -- Specializations for smart assignment (e.g., ["temporal", "migration", "api"])
    specializations JSONB NOT NULL DEFAULT '[]',
    -- Additional capabilities metadata
    capabilities JSONB NOT NULL DEFAULT '{}',
    -- Heartbeat tracking
    last_heartbeat TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Registration timestamp
    registered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for finding available agents quickly
CREATE INDEX IF NOT EXISTS idx_agents_available
ON genomai.agents (status, last_heartbeat DESC)
WHERE status = 'online';

-- Index for finding busy agents
CREATE INDEX IF NOT EXISTS idx_agents_busy
ON genomai.agents (current_task_issue)
WHERE status = 'busy';

-- Trigger to update updated_at on changes
CREATE OR REPLACE FUNCTION genomai.update_agents_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_agents_updated_at ON genomai.agents;
CREATE TRIGGER trigger_agents_updated_at
    BEFORE UPDATE ON genomai.agents
    FOR EACH ROW
    EXECUTE FUNCTION genomai.update_agents_updated_at();

-- Function to register an agent
CREATE OR REPLACE FUNCTION genomai.register_agent(
    p_agent_id TEXT,
    p_hostname TEXT,
    p_specializations JSONB DEFAULT '[]',
    p_capabilities JSONB DEFAULT '{}'
) RETURNS BOOLEAN AS $$
BEGIN
    -- Insert or update (upsert) agent registration
    INSERT INTO genomai.agents (agent_id, hostname, specializations, capabilities, status, last_heartbeat)
    VALUES (p_agent_id, p_hostname, p_specializations, p_capabilities, 'online', NOW())
    ON CONFLICT (agent_id) DO UPDATE SET
        hostname = EXCLUDED.hostname,
        specializations = EXCLUDED.specializations,
        capabilities = EXCLUDED.capabilities,
        status = 'online',
        last_heartbeat = NOW();

    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- Function to unregister an agent
CREATE OR REPLACE FUNCTION genomai.unregister_agent(
    p_agent_id TEXT
) RETURNS BOOLEAN AS $$
DECLARE
    v_count INT;
BEGIN
    -- Set agent offline (don't delete for history)
    UPDATE genomai.agents
    SET
        status = 'offline',
        current_task_issue = NULL
    WHERE agent_id = p_agent_id AND status != 'offline';

    GET DIAGNOSTICS v_count = ROW_COUNT;
    RETURN v_count > 0;
END;
$$ LANGUAGE plpgsql;

-- Function to update agent heartbeat
CREATE OR REPLACE FUNCTION genomai.agent_heartbeat(
    p_agent_id TEXT
) RETURNS BOOLEAN AS $$
DECLARE
    v_count INT;
BEGIN
    UPDATE genomai.agents
    SET last_heartbeat = NOW()
    WHERE agent_id = p_agent_id AND status IN ('online', 'busy');

    GET DIAGNOSTICS v_count = ROW_COUNT;
    RETURN v_count > 0;
END;
$$ LANGUAGE plpgsql;

-- Function to get available agents (online, not busy)
CREATE OR REPLACE FUNCTION genomai.get_available_agents(
    p_specialization TEXT DEFAULT NULL
) RETURNS TABLE (
    agent_id TEXT,
    hostname TEXT,
    specializations JSONB,
    last_heartbeat TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        a.agent_id,
        a.hostname,
        a.specializations,
        a.last_heartbeat
    FROM genomai.agents a
    WHERE
        a.status = 'online'
        AND a.last_heartbeat > NOW() - INTERVAL '5 minutes'
        AND (
            p_specialization IS NULL
            OR a.specializations ? p_specialization
        )
    ORDER BY a.last_heartbeat DESC;
END;
$$ LANGUAGE plpgsql;

-- Function to assign task to agent (smart assignment)
-- Returns agent_id if assigned, NULL if no available agents
CREATE OR REPLACE FUNCTION genomai.assign_task_to_agent(
    p_issue_number INT,
    p_required_specialization TEXT DEFAULT NULL
) RETURNS TEXT AS $$
DECLARE
    v_agent_id TEXT;
    v_claim_success BOOLEAN;
BEGIN
    -- Find best available agent
    -- Priority: 1) matching specialization, 2) most recent heartbeat
    SELECT a.agent_id INTO v_agent_id
    FROM genomai.agents a
    WHERE
        a.status = 'online'
        AND a.last_heartbeat > NOW() - INTERVAL '5 minutes'
    ORDER BY
        -- Prioritize agents with matching specialization
        CASE WHEN p_required_specialization IS NOT NULL
             AND a.specializations ? p_required_specialization
             THEN 0 ELSE 1 END,
        a.last_heartbeat DESC
    LIMIT 1
    FOR UPDATE SKIP LOCKED;

    IF v_agent_id IS NULL THEN
        RETURN NULL;
    END IF;

    -- Try to claim the task for this agent
    v_claim_success := genomai.claim_agent_task(p_issue_number, v_agent_id);

    IF NOT v_claim_success THEN
        RETURN NULL;
    END IF;

    -- Mark agent as busy
    UPDATE genomai.agents
    SET
        status = 'busy',
        current_task_issue = p_issue_number
    WHERE agent_id = v_agent_id;

    RETURN v_agent_id;
END;
$$ LANGUAGE plpgsql;

-- Function to release agent from task
CREATE OR REPLACE FUNCTION genomai.release_agent(
    p_agent_id TEXT
) RETURNS BOOLEAN AS $$
DECLARE
    v_count INT;
BEGIN
    UPDATE genomai.agents
    SET
        status = 'online',
        current_task_issue = NULL
    WHERE agent_id = p_agent_id AND status = 'busy';

    GET DIAGNOSTICS v_count = ROW_COUNT;
    RETURN v_count > 0;
END;
$$ LANGUAGE plpgsql;

-- Function to detect and release orphaned agents (no heartbeat for N minutes)
CREATE OR REPLACE FUNCTION genomai.release_orphaned_agents(
    p_timeout_minutes INT DEFAULT 10
) RETURNS INT AS $$
DECLARE
    v_count INT;
BEGIN
    UPDATE genomai.agents
    SET
        status = 'offline',
        current_task_issue = NULL
    WHERE
        status IN ('online', 'busy')
        AND last_heartbeat < NOW() - (p_timeout_minutes || ' minutes')::INTERVAL;

    GET DIAGNOSTICS v_count = ROW_COUNT;
    RETURN v_count;
END;
$$ LANGUAGE plpgsql;

-- Update agent_tasks to support labels for smart assignment
ALTER TABLE genomai.agent_tasks
ADD COLUMN IF NOT EXISTS labels JSONB NOT NULL DEFAULT '[]';

-- Index for label-based queries
CREATE INDEX IF NOT EXISTS idx_agent_tasks_labels
ON genomai.agent_tasks USING GIN (labels)
WHERE status = 'pending';

-- Comments for documentation
COMMENT ON TABLE genomai.agents IS 'Agent registry for multi-agent coordination (Phase 3)';
COMMENT ON FUNCTION genomai.register_agent IS 'Register or re-register an agent. Returns true on success.';
COMMENT ON FUNCTION genomai.unregister_agent IS 'Mark agent as offline. Returns true if agent was online.';
COMMENT ON FUNCTION genomai.agent_heartbeat IS 'Update agent heartbeat timestamp. Returns true if agent exists and is active.';
COMMENT ON FUNCTION genomai.get_available_agents IS 'Get list of available agents, optionally filtered by specialization.';
COMMENT ON FUNCTION genomai.assign_task_to_agent IS 'Smart assignment: find best agent for task and claim it. Returns agent_id or NULL.';
COMMENT ON FUNCTION genomai.release_agent IS 'Release agent from current task. Returns true on success.';
COMMENT ON FUNCTION genomai.release_orphaned_agents IS 'Mark agents without recent heartbeat as offline. Returns count of affected agents.';
