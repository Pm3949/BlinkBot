-- Migration: 008_share_keys.sql
-- Description: Adds share_keys boolean to user_settings table to allow sharing of API keys workspace-wide

ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS share_keys BOOLEAN DEFAULT FALSE;
