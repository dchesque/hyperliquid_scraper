-- Migration: 002_performance_indexes
-- Description: Additional performance indexes and optimizations
-- Date: 2024-01-02
-- Author: Hyperliquid Scraper System

-- ============================================================================
-- ADDITIONAL PERFORMANCE INDEXES
-- ============================================================================

-- Composite indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_funding_rates_latest_by_coin
    ON funding_rates(coin, scraped_at DESC)
    WHERE hyperliquid_funding IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_funding_rates_high_arbitrage
    ON funding_rates(scraped_at DESC, binance_hl_arb DESC, bybit_hl_arb DESC)
    WHERE ABS(COALESCE(binance_hl_arb, 0)) > 1 OR ABS(COALESCE(bybit_hl_arb, 0)) > 1;

CREATE INDEX IF NOT EXISTS idx_funding_rates_sentiment_analysis
    ON funding_rates(hyperliquid_sentiment, scraped_at DESC)
    WHERE hyperliquid_sentiment IS NOT NULL;

-- Partial indexes for active queries
CREATE INDEX IF NOT EXISTS idx_funding_rates_positive_funding
    ON funding_rates(hyperliquid_funding DESC, coin)
    WHERE hyperliquid_funding > 0;

CREATE INDEX IF NOT EXISTS idx_funding_rates_negative_funding
    ON funding_rates(hyperliquid_funding ASC, coin)
    WHERE hyperliquid_funding < 0;

-- Index for favorited coins
CREATE INDEX IF NOT EXISTS idx_funding_rates_favorited
    ON funding_rates(coin, scraped_at DESC)
    WHERE is_favorited = TRUE;

-- Open Interest ranking index
CREATE INDEX IF NOT EXISTS idx_funding_rates_oi_ranking
    ON funding_rates(timeframe, rank_by_oi, scraped_at DESC)
    WHERE rank_by_oi IS NOT NULL;

-- ============================================================================
-- MATERIALIZED VIEWS FOR PERFORMANCE
-- ============================================================================

-- Latest funding rates per coin (refreshed periodically)
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_latest_funding_rates AS
SELECT DISTINCT ON (coin, timeframe)
    id,
    coin,
    hyperliquid_oi,
    hyperliquid_funding,
    hyperliquid_sentiment,
    binance_funding,
    bybit_funding,
    binance_hl_arb,
    bybit_hl_arb,
    timeframe,
    rank_by_oi,
    is_favorited,
    scraped_at
FROM funding_rates
ORDER BY coin, timeframe, scraped_at DESC;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_latest_funding_rates_coin_timeframe
    ON mv_latest_funding_rates(coin, timeframe);

-- Hourly statistics view
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_hourly_stats AS
SELECT
    DATE_TRUNC('hour', scraped_at) as hour,
    timeframe,
    COUNT(DISTINCT coin) as total_coins,
    COUNT(*) FILTER (WHERE hyperliquid_funding > 0) as positive_funding_count,
    COUNT(*) FILTER (WHERE hyperliquid_funding < 0) as negative_funding_count,
    AVG(hyperliquid_funding) FILTER (WHERE hyperliquid_funding IS NOT NULL) as avg_funding,
    MAX(hyperliquid_funding) as max_funding,
    MIN(hyperliquid_funding) as min_funding,
    SUM(hyperliquid_oi) as total_open_interest,
    COUNT(*) FILTER (WHERE ABS(COALESCE(binance_hl_arb, 0)) > 1 OR ABS(COALESCE(bybit_hl_arb, 0)) > 1) as arbitrage_opportunities
FROM funding_rates
WHERE scraped_at >= NOW() - INTERVAL '7 days'
GROUP BY DATE_TRUNC('hour', scraped_at), timeframe;

CREATE INDEX IF NOT EXISTS idx_mv_hourly_stats_hour
    ON mv_hourly_stats(hour DESC);

-- Top movers view
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_top_movers AS
WITH latest_rates AS (
    SELECT DISTINCT ON (coin, timeframe)
        coin,
        timeframe,
        hyperliquid_funding,
        hyperliquid_oi,
        scraped_at
    FROM funding_rates
    WHERE scraped_at >= NOW() - INTERVAL '24 hours'
    ORDER BY coin, timeframe, scraped_at DESC
),
previous_rates AS (
    SELECT DISTINCT ON (coin, timeframe)
        coin,
        timeframe,
        hyperliquid_funding as previous_funding
    FROM funding_rates
    WHERE scraped_at >= NOW() - INTERVAL '48 hours'
        AND scraped_at < NOW() - INTERVAL '24 hours'
    ORDER BY coin, timeframe, scraped_at DESC
)
SELECT
    l.coin,
    l.timeframe,
    l.hyperliquid_funding as current_funding,
    p.previous_funding,
    (l.hyperliquid_funding - COALESCE(p.previous_funding, 0)) as funding_change,
    CASE
        WHEN p.previous_funding IS NOT NULL AND p.previous_funding != 0
        THEN ((l.hyperliquid_funding - p.previous_funding) / ABS(p.previous_funding) * 100)
        ELSE NULL
    END as change_percentage,
    l.hyperliquid_oi,
    l.scraped_at
FROM latest_rates l
LEFT JOIN previous_rates p ON l.coin = p.coin AND l.timeframe = p.timeframe
WHERE l.hyperliquid_funding IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_mv_top_movers_change
    ON mv_top_movers(change_percentage DESC NULLS LAST);

-- ============================================================================
-- PARTITIONING FOR LARGE TABLES (FUTURE)
-- ============================================================================

-- Note: Enable when table grows large (>100M rows)
-- Partition funding_rates by month
/*
CREATE TABLE funding_rates_partitioned (
    LIKE funding_rates INCLUDING ALL
) PARTITION BY RANGE (scraped_at);

-- Create monthly partitions
CREATE TABLE funding_rates_y2024m01 PARTITION OF funding_rates_partitioned
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE TABLE funding_rates_y2024m02 PARTITION OF funding_rates_partitioned
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');
*/

-- ============================================================================
-- RECORD MIGRATION
-- ============================================================================

INSERT INTO migrations (version, name, description, checksum)
VALUES (
    2,
    '002_performance_indexes',
    'Performance indexes and materialized views for optimized queries',
    MD5('002_performance_indexes_v1')
) ON CONFLICT (version) DO NOTHING;