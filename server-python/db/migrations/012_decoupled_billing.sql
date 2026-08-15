-- Create System AI Models Table
CREATE TABLE IF NOT EXISTS system_ai_models (
  id VARCHAR(100) PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  provider VARCHAR(50) NOT NULL,
  category VARCHAR(50) DEFAULT 'General',
  tier_badge VARCHAR(50) DEFAULT 'Low Burn',
  input_cost_per_1m NUMERIC(12, 6) DEFAULT 0.0,
  output_cost_per_1m NUMERIC(12, 6) DEFAULT 0.0,
  credits_per_1k_tokens NUMERIC(12, 6) DEFAULT 0.1,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Seed System AI Models Table with default models from old ai_models table
INSERT INTO system_ai_models (id, name, provider, category, credits_per_1k_tokens, is_active)
VALUES
  ('llama-3.3-70b-versatile', 'Llama 3.3 70B (Free - Smart)', 'groq', 'General', 0.0, TRUE),
  ('llama-3.1-8b-instant', 'Llama 3.1 8B (Free - Fast)', 'groq', 'Fast', 0.0, TRUE),
  ('deepseek-r1-distill-llama-70b', 'DeepSeek R1 Distill 70B (Free)', 'groq', 'Reasoning', 0.0, TRUE),
  ('mixtral-8x7b-32768', 'Mixtral 8x7B (Large Context)', 'groq', 'General', 0.0, TRUE),
  ('qwen-2.5-32b', 'Qwen 2.5 32B (Coding/Logic)', 'groq', 'Coding', 0.0, TRUE),
  ('gemma2-9b-it', 'Gemma 2 9B (Free - Google)', 'groq', 'Fast', 0.0, TRUE),
  ('gemini-2.0-flash-exp', 'Gemini 2.0 Flash (Fast / Multimodal)', 'gemini', 'Fast', 0.1, TRUE),
  ('gemini-1.5-pro', 'Gemini 1.5 Pro (2M Token Context)', 'gemini', 'Reasoning', 0.5, TRUE),
  ('gemini-1.5-flash', 'Gemini 1.5 Flash (Lightweight)', 'gemini', 'Fast', 0.1, TRUE),
  ('gpt-4o', 'GPT-4o (Paid - Flagship)', 'openai', 'Reasoning', 1.0, TRUE),
  ('gpt-4o-mini', 'GPT-4o Mini (Paid - Fast)', 'openai', 'Fast', 0.1, TRUE),
  ('claude-3-5-sonnet-20241022', 'Claude 3.5 Sonnet (Paid - Flagship)', 'anthropic', 'Reasoning', 1.5, TRUE)
ON CONFLICT (id) DO NOTHING;

-- Create User Custom Models Table
CREATE TABLE IF NOT EXISTS user_ai_models (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
  name VARCHAR(100) NOT NULL,
  provider VARCHAR(50) NOT NULL,
  model_identifier VARCHAR(100) NOT NULL,
  base_url TEXT NOT NULL,
  api_key TEXT, -- Encrypted
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create User Wallets Table
CREATE TABLE IF NOT EXISTS user_wallets (
  user_id UUID PRIMARY KEY REFERENCES public.users(id) ON DELETE CASCADE,
  credit_balance NUMERIC(12, 4) DEFAULT 0.0000,
  auto_recharge_enabled BOOLEAN DEFAULT FALSE,
  recharge_threshold NUMERIC(12, 4) DEFAULT 10.0000,
  recharge_amount_usd NUMERIC(10, 2) DEFAULT 20.00,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create Credit Transactions Table
CREATE TABLE IF NOT EXISTS credit_transactions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
  agent_id UUID REFERENCES agents(id) ON DELETE SET NULL,
  amount_credits NUMERIC(12, 4) NOT NULL,
  transaction_type VARCHAR(50) NOT NULL, -- 'topup', 'usage_deduction', 'refund'
  model_used VARCHAR(100),
  prompt_tokens INT DEFAULT 0,
  completion_tokens INT DEFAULT 0,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Add allow_byok to user subscriptions
ALTER TABLE user_subscriptions ADD COLUMN IF NOT EXISTS allow_byok BOOLEAN DEFAULT FALSE;

-- Add use_byok to agents
ALTER TABLE agents ADD COLUMN IF NOT EXISTS use_byok BOOLEAN DEFAULT FALSE;

