-- Composite index on chat_messages to accelerate paginated message fetches (newest-first/DESC ordering)
CREATE INDEX IF NOT EXISTS idx_chat_messages_session_created 
ON chat_messages(session_id, created_at DESC);

-- Composite index on chat_sessions for workspace sidebars (ordering pinned first, then last updated descending)
CREATE INDEX IF NOT EXISTS idx_chat_sessions_workspace_user_pinned 
ON chat_sessions(workspace_id, user_id, pinned DESC, updated_at DESC);
