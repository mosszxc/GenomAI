-- Migration: 046_ideas_hash_constraint.sql
-- Issue: #698
-- Purpose: Remove test idea with invalid canonical_hash and add length constraint

-- Remove test record with invalid hash
DELETE FROM genomai.ideas
WHERE id = '00000000-0000-0000-0000-000000000003'
  AND canonical_hash = 'test_without_schema';

-- Add constraint: canonical_hash must be 64 chars (SHA256) or NULL
ALTER TABLE genomai.ideas
ADD CONSTRAINT ideas_canonical_hash_length
CHECK (canonical_hash IS NULL OR LENGTH(canonical_hash) = 64);
