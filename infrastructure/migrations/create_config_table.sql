-- Migration: create_config_table
-- Description: Create config table for storing API keys, URLs, and other configuration values
-- Purpose: Centralized storage for n8n workflows (basic plan doesn't support env vars)
-- Schema: genomai

-- ============================================
-- Config Table (Mutable)
-- ============================================

CREATE TABLE IF NOT EXISTS genomai.config (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  key text NOT NULL UNIQUE,
  value text NOT NULL,
  description text,
  is_secret boolean NOT NULL DEFAULT false,
  created_at timestamp NOT NULL DEFAULT now(),
  updated_at timestamp NOT NULL DEFAULT now()
);

-- ============================================
-- Indexes for Performance
-- ============================================

-- Index for key lookups (most common query)
CREATE INDEX IF NOT EXISTS idx_config_key 
ON genomai.config(key);

-- ============================================
-- Constraints & Rules
-- ============================================

-- Add comment to table
COMMENT ON TABLE genomai.config IS 'Configuration table for storing API keys, URLs, and other config values. Used by n8n workflows on basic plan.';

-- Add comments to columns
COMMENT ON COLUMN genomai.config.id IS 'Primary key, auto-generated UUID';
COMMENT ON COLUMN genomai.config.key IS 'Configuration key (e.g., decision_engine_api_url, decision_engine_api_key)';
COMMENT ON COLUMN genomai.config.value IS 'Configuration value (can contain secrets)';
COMMENT ON COLUMN genomai.config.description IS 'Human-readable description of the config entry';
COMMENT ON COLUMN genomai.config.is_secret IS 'Whether this value is a secret (for UI masking)';
COMMENT ON COLUMN genomai.config.created_at IS 'Timestamp when config entry was created';
COMMENT ON COLUMN genomai.config.updated_at IS 'Timestamp when config entry was last updated';

-- ============================================
-- Initial Data (Decision Engine Config)
-- ============================================

-- Insert Decision Engine API URL (public, not secret)
INSERT INTO genomai.config (key, value, description, is_secret) VALUES
  ('decision_engine_api_url', 'https://genomai.onrender.com', 'Decision Engine API URL', false)
ON CONFLICT (key) DO UPDATE SET 
  value = EXCLUDED.value,
  description = EXCLUDED.description,
  updated_at = now();

-- Insert Decision Engine API Key (secret - user must update this!)
INSERT INTO genomai.config (key, value, description, is_secret) VALUES
  ('decision_engine_api_key', 'REPLACE_WITH_YOUR_API_KEY', 'Decision Engine API Key for authentication', true)
ON CONFLICT (key) DO UPDATE SET 
  value = EXCLUDED.value,
  description = EXCLUDED.description,
  updated_at = now();

