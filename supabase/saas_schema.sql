-- Qbit-Bot Sovereign SaaS Schema v5.0
-- Run this in your Supabase SQL Editor

-- 1. Profiles Table (Extended User Info)
CREATE TABLE profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    full_name TEXT,
    organization_name TEXT,
    tier TEXT DEFAULT 'Standard', -- Standard, Institutional, Sovereign
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Trading Accounts (The Bridge)
CREATE TABLE trading_accounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    account_number BIGINT NOT NULL,
    broker_name TEXT NOT NULL,
    server_name TEXT NOT NULL,
    password_encrypted TEXT, -- To be used with Cloud Bridge
    api_token TEXT, -- Optional: For MetaApi integration
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, account_number)
);

-- 3. Sovereign Configuration (AI-Tuning per Account)
CREATE TABLE sovereign_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    account_id UUID REFERENCES trading_accounts(id) ON DELETE CASCADE,
    rsi_oversold INT DEFAULT 30,
    rsi_overbought INT DEFAULT 70,
    sl_points INT DEFAULT 150,
    tp_points INT DEFAULT 300,
    max_spread_pips INT DEFAULT 20,
    ai_adjustment_count INT DEFAULT 0,
    last_ai_update TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. Unified Trade Journal (Auditable Trail)
CREATE TABLE trade_journal (
    id BIGSERIAL PRIMARY KEY,
    account_id UUID REFERENCES trading_accounts(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    strategy TEXT NOT NULL,
    decision TEXT NOT NULL, -- ENTRY, SKIP, BLOCK, EXIT, PAUSE
    reason TEXT,
    technical_snapshot JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. AI optimization Notes (Per Account)
CREATE TABLE ai_optimization_notes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    account_id UUID REFERENCES trading_accounts(id) ON DELETE CASCADE,
    strategic_note TEXT,
    overall_health_score INT,
    suggested_tweaks JSONB,
    identified_patterns JSONB,
    last_audit TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 6. Global Market Intelligence (Unified Dashboard Feed)
CREATE TABLE market_intelligence (
    id SERIAL PRIMARY KEY,
    pair TEXT NOT NULL,
    technical_summary TEXT,
    sentiment_score INT,
    ai_note TEXT,
    matrix JSONB,
    yf_stats JSONB,
    last_update TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 7. Row Level Security (RLS) Configuration
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE trading_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE sovereign_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE trade_journal ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_optimization_notes ENABLE ROW LEVEL SECURITY;
ALTER TABLE market_intelligence ENABLE ROW LEVEL SECURITY;

-- 🛡️ Security Policies: Users can only see their own data
CREATE POLICY "Users can view own profile" ON profiles FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Users can view own accounts" ON trading_accounts FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can view own configs" ON sovereign_configs FOR SELECT USING (
    account_id IN (SELECT id FROM trading_accounts WHERE user_id = auth.uid())
);
CREATE POLICY "Users can view own journals" ON trade_journal FOR SELECT USING (
    account_id IN (SELECT id FROM trading_accounts WHERE user_id = auth.uid())
);
CREATE POLICY "Users can view own AI notes" ON ai_optimization_notes FOR SELECT USING (
    account_id IN (SELECT id FROM trading_accounts WHERE user_id = auth.uid())
);
CREATE POLICY "Anyone can view market intelligence" ON market_intelligence FOR SELECT USING (true);
