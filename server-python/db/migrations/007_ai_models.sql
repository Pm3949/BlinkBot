-- 007_ai_models.sql
-- Table for dynamic AI Models Catalog

CREATE TABLE IF NOT EXISTS ai_models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider VARCHAR(50) NOT NULL,
    model_id VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    requires_key BOOLEAN DEFAULT FALSE,
    base_url TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    category VARCHAR(50) DEFAULT 'General',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Seed default models across all major cloud providers
INSERT INTO ai_models (provider, model_id, name, description, requires_key, category, is_active)
VALUES 
    -- Groq Models (Free)
    ('groq', 'llama-3.3-70b-versatile', 'Llama 3.3 70B (Free - Smart)', 'High intelligence 70B model powered by Groq', FALSE, 'General', TRUE),
    ('groq', 'llama-3.1-8b-instant', 'Llama 3.1 8B (Free - Fast)', 'Fast, low-latency open model powered by Groq', FALSE, 'Fast', TRUE),
    ('groq', 'deepseek-r1-distill-llama-70b', 'DeepSeek R1 Distill 70B (Free)', 'Reasoning model powered by Groq Llama 70B', FALSE, 'Reasoning', TRUE),
    ('groq', 'mixtral-8x7b-32768', 'Mixtral 8x7B (Large Context)', 'High context window mixture of experts model', FALSE, 'General', TRUE),
    ('groq', 'qwen-2.5-32b', 'Qwen 2.5 32B (Coding/Logic)', 'Alibaba Qwen model optimized for coding & logic', FALSE, 'Coding', TRUE),
    ('groq', 'gemma2-9b-it', 'Gemma 2 9B (Free - Google)', 'Google lightweight open model via Groq', FALSE, 'Fast', TRUE),

    -- OpenRouter Models (Free Tier with OpenRouter API Key)
    ('openrouter', 'deepseek/deepseek-r1:free', 'DeepSeek R1 (Free - OpenRouter)', 'DeepSeek reasoning model via OpenRouter free tier', TRUE, 'Reasoning', FALSE),
    ('openrouter', 'deepseek/deepseek-chat:free', 'DeepSeek V3 (Free - OpenRouter)', 'DeepSeek flagship chat model via OpenRouter free tier', TRUE, 'General', FALSE),
    ('openrouter', 'meta-llama/llama-3.3-70b-instruct:free', 'Llama 3.3 70B (Free - OpenRouter)', 'Meta flagship open model via OpenRouter free tier', TRUE, 'General', FALSE),
    ('openrouter', 'qwen/qwen-2.5-coder-32b-instruct:free', 'Qwen 2.5 Coder 32B (Free - OpenRouter)', 'Alibaba flagship coding model via OpenRouter free tier', TRUE, 'Coding', FALSE),
    ('openrouter', 'google/gemini-2.0-flash-exp:free', 'Gemini 2.0 Flash (Free - OpenRouter)', 'Google Flash experimental model via OpenRouter free tier', TRUE, 'Fast', FALSE),

    -- OpenAI Models (Paid)
    ('openai', 'gpt-4o', 'GPT-4o (Paid - Flagship)', 'OpenAI flagship multimodal reasoning model', TRUE, 'Reasoning', FALSE),
    ('openai', 'gpt-4o-mini', 'GPT-4o Mini (Paid - Fast)', 'Fast, cost-effective OpenAI flagship mini model', TRUE, 'Fast', FALSE),
    ('openai', 'o1', 'OpenAI o1 (Paid - Advanced Reasoning)', 'Advanced reasoning model for complex STEM & coding', TRUE, 'Reasoning', FALSE),
    ('openai', 'o1-mini', 'OpenAI o1 Mini (Paid - Fast Reasoning)', 'Fast reasoning model for coding and STEM queries', TRUE, 'Fast', FALSE),
    ('openai', 'gpt-4-turbo', 'GPT-4 Turbo (Paid - Vision)', 'High capability GPT-4 Turbo model with vision support', TRUE, 'General', FALSE),

    -- Anthropic Claude Models (Paid)
    ('anthropic', 'claude-3-5-sonnet-20241022', 'Claude 3.5 Sonnet (Paid - Flagship)', 'Anthropic flagship reasoning and coding model', TRUE, 'Reasoning', FALSE),
    ('anthropic', 'claude-3-5-haiku-20241022', 'Claude 3.5 Haiku (Paid - Fast)', 'Anthropic lightning fast lightweight model', TRUE, 'Fast', FALSE),
    ('anthropic', 'claude-3-opus-20240229', 'Claude 3 Opus (Paid - High Intelligence)', 'Anthropic most intelligent model for complex tasks', TRUE, 'Reasoning', FALSE),

    -- Google Gemini Models (Paid / API Key)
    ('gemini', 'gemini-2.0-flash', 'Gemini 2.0 Flash (Next-Gen Production)', 'Google latest production high speed multimodal model', TRUE, 'Fast', FALSE),
    ('gemini', 'gemini-2.0-flash-exp', 'Gemini 2.0 Flash Exp (Experimental)', 'Google next-gen experimental multimodal model', TRUE, 'Fast', FALSE),
    ('gemini', 'gemini-1.5-pro', 'Gemini 1.5 Pro (2M Token Context)', 'Google flagship model with massive 2M token context', TRUE, 'Reasoning', FALSE),
    ('gemini', 'gemini-1.5-flash', 'Gemini 1.5 Flash (Lightweight)', 'Google fast and efficient model for general tasks', TRUE, 'Fast', FALSE),

    -- HuggingFace Models
    ('huggingface', 'meta-llama/Llama-3.3-70B-Instruct', 'Llama 3.3 70B (HF Endpoint)', 'HuggingFace inference endpoint model', TRUE, 'General', FALSE),
    ('huggingface', 'Qwen/Qwen2.5-Coder-32B-Instruct', 'Qwen 2.5 Coder 32B (HF Endpoint)', 'HuggingFace coding inference endpoint model', TRUE, 'Coding', FALSE),
    ('huggingface', 'deepseek-ai/DeepSeek-R1-Distill-Qwen-32B', 'DeepSeek R1 Qwen 32B (HF Endpoint)', 'HuggingFace DeepSeek reasoning model endpoint', TRUE, 'Reasoning', FALSE)
ON CONFLICT (model_id) DO NOTHING;
