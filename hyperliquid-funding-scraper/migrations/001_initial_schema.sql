-- Migration: 001_initial_schema
-- Description: Create initial database schema for Hyperliquid Funding Scraper
-- Date: 2024-01-01
-- Author: Hyperliquid Scraper System

-- ============================================================================
-- MIGRATIONS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS migrations (
    id SERIAL PRIMARY KEY,
    version INTEGER NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    execution_time_ms INTEGER,
    checksum VARCHAR(64),
    status VARCHAR(20) DEFAULT 'completed',
    rollback_executed BOOLEAN DEFAULT FALSE,
    rollback_at TIMESTAMP WITH TIME ZONE,
    description TEXT
);

-- ============================================================================
-- MAIN TABLES
-- ============================================================================

-- Funding Rates Table
CREATE TABLE IF NOT EXISTS funding_rates (
    id BIGSERIAL PRIMARY KEY,
    coin VARCHAR(20) NOT NULL,
    hyperliquid_oi DECIMAL(20, 2),
    hyperliquid_funding DECIMAL(10, 6),
    hyperliquid_sentiment VARCHAR(10) CHECK (hyperliquid_sentiment IN ('positive', 'negative', 'neutral')),
    binance_funding DECIMAL(10, 6),
    bybit_funding DECIMAL(10, 6),
    binance_hl_arb DECIMAL(10, 6),
    bybit_hl_arb DECIMAL(10, 6),
    timeframe VARCHAR(10) NOT NULL CHECK (timeframe IN ('hourly', '8hours', 'day', 'week', 'year')),
    rank_by_oi INTEGER CHECK (rank_by_oi > 0),
    is_favorited BOOLEAN DEFAULT FALSE,
    scraped_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT unique_funding_rate UNIQUE(coin, timeframe, scraped_at)
);

-- Scraping Logs Table
CREATE TABLE IF NOT EXISTS scraping_logs (
    id BIGSERIAL PRIMARY KEY,
    status VARCHAR(20) CHECK (status IN ('success', 'partial', 'failed')),
    coins_scraped INTEGER DEFAULT 0,
    duration_seconds DECIMAL(10, 2),
    error_message TEXT,
    timeframe VARCHAR(10),
    total_coins_found INTEGER,
    arbitrage_opportunities INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB
);

-- Coin Information Table (for tracking coin metadata)
CREATE TABLE IF NOT EXISTS coins (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(100),
    category VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    first_seen_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_seen_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    total_scrapes INTEGER DEFAULT 0,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Arbitrage Alerts Table
CREATE TABLE IF NOT EXISTS arbitrage_alerts (
    id BIGSERIAL PRIMARY KEY,
    coin VARCHAR(20) NOT NULL,
    exchange VARCHAR(20) NOT NULL,
    hyperliquid_funding DECIMAL(10, 6),
    exchange_funding DECIMAL(10, 6),
    arbitrage_value DECIMAL(10, 6) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    alert_threshold DECIMAL(10, 6),
    is_notified BOOLEAN DEFAULT FALSE,
    notified_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    funding_rate_id BIGINT REFERENCES funding_rates(id) ON DELETE CASCADE
);

-- System Metrics Table (for monitoring)
CREATE TABLE IF NOT EXISTS system_metrics (
    id BIGSERIAL PRIMARY KEY,
    metric_type VARCHAR(50) NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(20, 6),
    metric_unit VARCHAR(20),
    timeframe VARCHAR(20),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB
);

-- ============================================================================
-- INDEXES
-- ============================================================================

-- Funding Rates Indexes
CREATE INDEX IF NOT EXISTS idx_funding_rates_coin ON funding_rates(coin);
CREATE INDEX IF NOT EXISTS idx_funding_rates_timeframe ON funding_rates(timeframe);
CREATE INDEX IF NOT EXISTS idx_funding_rates_scraped_at ON funding_rates(scraped_at DESC);
CREATE INDEX IF NOT EXISTS idx_funding_rates_created_at ON funding_rates(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_funding_rates_coin_timeframe ON funding_rates(coin, timeframe);
CREATE INDEX IF NOT EXISTS idx_funding_rates_arbitrage ON funding_rates(binance_hl_arb, bybit_hl_arb)
    WHERE binance_hl_arb IS NOT NULL OR bybit_hl_arb IS NOT NULL;

-- Scraping Logs Indexes
CREATE INDEX IF NOT EXISTS idx_scraping_logs_created_at ON scraping_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_scraping_logs_status ON scraping_logs(status);
CREATE INDEX IF NOT EXISTS idx_scraping_logs_timeframe ON scraping_logs(timeframe);

-- Coins Indexes
CREATE INDEX IF NOT EXISTS idx_coins_symbol ON coins(symbol);
CREATE INDEX IF NOT EXISTS idx_coins_is_active ON coins(is_active);
CREATE INDEX IF NOT EXISTS idx_coins_last_seen ON coins(last_seen_at DESC);

-- Arbitrage Alerts Indexes
CREATE INDEX IF NOT EXISTS idx_arbitrage_alerts_coin ON arbitrage_alerts(coin);
CREATE INDEX IF NOT EXISTS idx_arbitrage_alerts_created_at ON arbitrage_alerts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_arbitrage_alerts_value ON arbitrage_alerts(arbitrage_value DESC);
CREATE INDEX IF NOT EXISTS idx_arbitrage_alerts_notified ON arbitrage_alerts(is_notified);

-- System Metrics Indexes
CREATE INDEX IF NOT EXISTS idx_system_metrics_type ON system_metrics(metric_type);
CREATE INDEX IF NOT EXISTS idx_system_metrics_created_at ON system_metrics(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_system_metrics_type_name ON system_metrics(metric_type, metric_name);

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Update timestamp trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply update trigger to funding_rates
CREATE TRIGGER update_funding_rates_updated_at BEFORE UPDATE ON funding_rates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Apply update trigger to coins
CREATE TRIGGER update_coins_updated_at BEFORE UPDATE ON coins
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE funding_rates IS 'Stores funding rate data scraped from Hyperliquid and other exchanges';
COMMENT ON TABLE scraping_logs IS 'Logs each scraping operation with performance metrics';
COMMENT ON TABLE coins IS 'Metadata about cryptocurrencies tracked by the system';
COMMENT ON TABLE arbitrage_alerts IS 'Tracks arbitrage opportunities detected between exchanges';
COMMENT ON TABLE system_metrics IS 'System performance and business metrics for monitoring';
COMMENT ON TABLE migrations IS 'Tracks database migrations execution history';

COMMENT ON COLUMN funding_rates.hyperliquid_oi IS 'Open Interest in USD on Hyperliquid';
COMMENT ON COLUMN funding_rates.hyperliquid_sentiment IS 'Market sentiment based on funding rate (positive/negative/neutral)';
COMMENT ON COLUMN funding_rates.binance_hl_arb IS 'Arbitrage opportunity between Binance and Hyperliquid (%)';
COMMENT ON COLUMN funding_rates.bybit_hl_arb IS 'Arbitrage opportunity between Bybit and Hyperliquid (%)';

-- ============================================================================
-- RECORD MIGRATION
-- ============================================================================

INSERT INTO migrations (version, name, description, checksum)
VALUES (
    1,
    '001_initial_schema',
    'Initial database schema with all base tables and indexes',
    MD5('001_initial_schema_v1')
) ON CONFLICT (version) DO NOTHING;