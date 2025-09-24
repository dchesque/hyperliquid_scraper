-- Rollback Migration: 002_performance_indexes
-- Description: Rollback performance indexes and materialized views
-- Date: 2024-01-02
-- Author: Hyperliquid Scraper System

-- ============================================================================
-- DROP MATERIALIZED VIEWS
-- ============================================================================

DROP MATERIALIZED VIEW IF EXISTS mv_top_movers CASCADE;
DROP MATERIALIZED VIEW IF EXISTS mv_hourly_stats CASCADE;
DROP MATERIALIZED VIEW IF EXISTS mv_latest_funding_rates CASCADE;

-- ============================================================================
-- DROP PERFORMANCE INDEXES
-- ============================================================================

-- Open Interest ranking index
DROP INDEX IF EXISTS idx_funding_rates_oi_ranking;

-- Favorited coins index
DROP INDEX IF EXISTS idx_funding_rates_favorited;

-- Partial indexes for funding
DROP INDEX IF EXISTS idx_funding_rates_negative_funding;
DROP INDEX IF EXISTS idx_funding_rates_positive_funding;

-- Sentiment analysis index
DROP INDEX IF EXISTS idx_funding_rates_sentiment_analysis;

-- High arbitrage index
DROP INDEX IF EXISTS idx_funding_rates_high_arbitrage;

-- Latest by coin index
DROP INDEX IF EXISTS idx_funding_rates_latest_by_coin;

-- ============================================================================
-- UPDATE MIGRATION LOG
-- ============================================================================

UPDATE migrations
SET rollback_executed = TRUE,
    rollback_at = NOW()
WHERE version = 2;