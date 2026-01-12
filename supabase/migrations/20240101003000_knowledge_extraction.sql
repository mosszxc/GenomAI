-- Migration: 030_knowledge_extraction
-- Issue: Knowledge Extraction System
-- Description: Tables for extracting knowledge from training transcripts

-- Knowledge sources (training transcripts)
CREATE TABLE IF NOT EXISTS genomai.knowledge_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_type TEXT NOT NULL CHECK (source_type IN ('youtube', 'file', 'manual')),
    title TEXT NOT NULL,
    url TEXT,
    transcript_text TEXT NOT NULL,
    language TEXT DEFAULT 'en',
    processed BOOLEAN DEFAULT false,
    processed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    created_by TEXT  -- admin telegram_id
);

-- Extracted knowledge items (pending review)
CREATE TABLE IF NOT EXISTS genomai.knowledge_extractions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID REFERENCES genomai.knowledge_sources(id) ON DELETE CASCADE,
    knowledge_type TEXT NOT NULL CHECK (knowledge_type IN (
        'premise', 'creative_attribute', 'process_rule', 'component_weight'
    )),
    -- LLM-extracted content
    name TEXT NOT NULL,
    description TEXT,
    payload JSONB NOT NULL,
    confidence_score NUMERIC(3,2) CHECK (confidence_score >= 0 AND confidence_score <= 1),
    -- Supporting quotes from transcript
    supporting_quotes TEXT[],
    -- Review workflow
    status TEXT DEFAULT 'pending' CHECK (status IN (
        'pending', 'approved', 'rejected', 'applied'
    )),
    reviewed_by TEXT,  -- admin telegram_id
    reviewed_at TIMESTAMPTZ,
    review_notes TEXT,
    -- Application tracking
    applied_at TIMESTAMPTZ,
    applied_to TEXT,  -- Target entity ID after application
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_knowledge_sources_processed
    ON genomai.knowledge_sources(processed);

CREATE INDEX IF NOT EXISTS idx_knowledge_extractions_status
    ON genomai.knowledge_extractions(status);

CREATE INDEX IF NOT EXISTS idx_knowledge_extractions_source
    ON genomai.knowledge_extractions(source_id);

CREATE INDEX IF NOT EXISTS idx_knowledge_extractions_type
    ON genomai.knowledge_extractions(knowledge_type);

-- Comments
COMMENT ON TABLE genomai.knowledge_sources IS 'Training transcript sources (YouTube courses, etc.)';
COMMENT ON TABLE genomai.knowledge_extractions IS 'LLM-extracted knowledge pending review';
COMMENT ON COLUMN genomai.knowledge_extractions.payload IS 'Type-specific structured data (premise fields, attribute values, etc.)';
COMMENT ON COLUMN genomai.knowledge_extractions.confidence_score IS 'LLM confidence in extraction (0.0-1.0)';
