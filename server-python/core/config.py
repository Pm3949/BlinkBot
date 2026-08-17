"""
================================================================================
RAGMATE CENTRAL CONFIGURATION FILE (config.py)
================================================================================

INSTRUCTIONS & IMPORTANT CONSIDERATIONS WHEN CHANGING VALUES:
1. Provider and Model Alignment:
   - When updating the DEFAULT_LLM_MODEL, ensure that the DEFAULT_LLM_PROVIDER matches the service hosting it (e.g., 'gemini' for 'gemini-3-flash', 'groq' for 'llama-3.3-70b-versatile').

2. Frontend Synchronization:
   - Default values configured here MUST match the initial options defined in frontend wizards:
     - client/src/components/agents/CreateAgentWizard.jsx
     - admin-client/src/components/agents/CreateAgentWizard.jsx
     - client/src/pages/AgentSettingsPage.jsx

3. Database Constraints:
   - The defaults set here should align with the SQL DEFAULT definitions inside server-python/database_schema.sql (e.g. default values for 'provider' and 'model' columns in the 'agents' table).

4. Environment Variables:
   - Make sure that API keys for the chosen default provider (e.g. GEMINI_API_KEY, GROQ_API_KEY) are set in your environment / docker-compose environment blocks.
"""

# Default LLM configurations
DEFAULT_LLM_PROVIDER = "groq"
DEFAULT_LLM_MODEL = "qwen/qwen3.6-27b"

# Fallback configurations
FALLBACK_GROQ_MODEL = "qwen/qwen3.6-27b"

# Default Vector Embedding configurations
DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
DEFAULT_CHUNK_STRATEGY = "sentence"
