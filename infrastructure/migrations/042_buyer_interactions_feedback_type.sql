-- Migration: 042_buyer_interactions_feedback_type.sql
-- Issue: #586 - Add 'feedback' to message_type constraint
-- Description: Allows logging /feedback command interactions

ALTER TABLE genomai.buyer_interactions DROP CONSTRAINT IF EXISTS buyer_interactions_message_type_check;

ALTER TABLE genomai.buyer_interactions ADD CONSTRAINT buyer_interactions_message_type_check
  CHECK (message_type IN ('text', 'video', 'photo', 'document', 'command', 'callback', 'system', 'feedback'));
