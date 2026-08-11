-- Migration: 011_add_nvidia_nim_api_key.sql
-- Description: Adds nvidia_api_key to user_settings table to support NVIDIA NIM
ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS nvidia_api_key TEXT;
