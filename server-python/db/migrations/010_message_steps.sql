-- Migration 010: Add steps JSONB column to chat_messages for persisting agent execution trace
ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS steps JSONB DEFAULT NULL;
