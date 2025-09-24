-- Rollback Migration: 001_initial_schema
-- Description: Rollback initial database schema
-- Date: 2024-01-01
-- Author: Hyperliquid Scraper System

-- ============================================================================
-- DROP TRIGGERS
-- ============================================================================

DROP TRIGGER IF EXISTS update_funding_rates_updated_at ON funding_rates;
DROP TRIGGER IF EXISTS update_coins_updated_at ON coins;

-- ============================================================================
-- DROP FUNCTIONS
-- ============================================================================

DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;

-- ============================================================================
-- DROP INDEXES
-- ============================================================================

-- System Metrics Indexes
DROP INDEX IF EXISTS idx_system_metrics_type_name;
DROP INDEX IF EXISTS idx_system_metrics_created_at;
DROP INDEX IF EXISTS idx_system_metrics_type;

-- Arbitrage Alerts Indexes
DROP INDEX IF EXISTS idx_arbitrage_alerts_notified;
DROP INDEX IF EXISTS idx_arbitrage_alerts_value;
DROP INDEX IF EXISTS idx_arbitrage_alerts_created_at;
DROP INDEX IF EXISTS idx_arbitrage_alerts_coin;

-- Coins Indexes
DROP INDEX IF EXISTS idx_coins_last_seen;
DROP INDEX IF EXISTS idx_coins_is_active;
DROP INDEX IF EXISTS idx_coins_symbol;

-- Scraping Logs Indexes
DROP INDEX IF EXISTS idx_scraping_logs_timeframe;
DROP INDEX IF EXISTS idx_scraping_logs_status;
DROP INDEX IF EXISTS idx_scraping_logs_created_at;

-- Funding Rates Indexes
DROP INDEX IF EXISTS idx_funding_rates_arbitrage;
DROP INDEX IF EXISTS idx_funding_rates_coin_timeframe;
DROP INDEX IF EXISTS idx_funding_rates_created_at;
DROP INDEX IF EXISTS idx_funding_rates_scraped_at;
DROP INDEX IF EXISTS idx_funding_rates_timeframe;
DROP INDEX IF EXISTS idx_funding_rates_coin;

-- ============================================================================
-- DROP TABLES
-- ============================================================================

DROP TABLE IF EXISTS system_metrics CASCADE;
DROP TABLE IF EXISTS arbitrage_alerts CASCADE;
DROP TABLE IF EXISTS coins CASCADE;
DROP TABLE IF EXISTS scraping_logs CASCADE;
DROP TABLE IF EXISTS funding_rates CASCADE;
DROP TABLE IF EXISTS migrations CASCADE;

-- ============================================================================
-- UPDATE MIGRATION LOG
-- ============================================================================

-- Note: This would normally update the migrations table,
-- but since we're dropping it, we can't record the rollback
-- In production, you might want to keep migrations table separate