-- Migration: 004_seed_data
-- Description: Seed initial data and configuration
-- Date: 2024-01-04
-- Author: Hyperliquid Scraper System

-- ============================================================================
-- SEED COIN DATA
-- ============================================================================

-- Insert common cryptocurrencies
INSERT INTO coins (symbol, name, category, is_active, metadata) VALUES
    ('BTC', 'Bitcoin', 'Layer 1', TRUE, '{"market_cap_rank": 1, "tags": ["store-of-value", "pow"]}'),
    ('ETH', 'Ethereum', 'Layer 1', TRUE, '{"market_cap_rank": 2, "tags": ["smart-contracts", "defi"]}'),
    ('SOL', 'Solana', 'Layer 1', TRUE, '{"market_cap_rank": 5, "tags": ["high-performance", "web3"]}'),
    ('BNB', 'BNB', 'Exchange', TRUE, '{"market_cap_rank": 4, "tags": ["exchange-token", "bsc"]}'),
    ('XRP', 'Ripple', 'Payment', TRUE, '{"market_cap_rank": 6, "tags": ["payments", "cbdc"]}'),
    ('ADA', 'Cardano', 'Layer 1', TRUE, '{"market_cap_rank": 7, "tags": ["pos", "academic"]}'),
    ('AVAX', 'Avalanche', 'Layer 1', TRUE, '{"market_cap_rank": 10, "tags": ["subnets", "defi"]}'),
    ('MATIC', 'Polygon', 'Layer 2', TRUE, '{"market_cap_rank": 13, "tags": ["ethereum-scaling", "zk"]}'),
    ('DOT', 'Polkadot', 'Layer 0', TRUE, '{"market_cap_rank": 11, "tags": ["interoperability", "parachains"]}'),
    ('LINK', 'Chainlink', 'Oracle', TRUE, '{"market_cap_rank": 12, "tags": ["oracle", "defi-infrastructure"]}'),
    ('UNI', 'Uniswap', 'DeFi', TRUE, '{"market_cap_rank": 20, "tags": ["dex", "amm"]}'),
    ('ARB', 'Arbitrum', 'Layer 2', TRUE, '{"market_cap_rank": 30, "tags": ["ethereum-scaling", "optimistic-rollup"]}'),
    ('OP', 'Optimism', 'Layer 2', TRUE, '{"market_cap_rank": 31, "tags": ["ethereum-scaling", "optimistic-rollup"]}'),
    ('INJ', 'Injective', 'DeFi', TRUE, '{"market_cap_rank": 40, "tags": ["derivatives", "cosmos"]}'),
    ('SUI', 'Sui', 'Layer 1', TRUE, '{"market_cap_rank": 35, "tags": ["move", "parallel-execution"]}'),
    ('APT', 'Aptos', 'Layer 1', TRUE, '{"market_cap_rank": 36, "tags": ["move", "parallel-execution"]}'),
    ('SEI', 'Sei', 'DeFi', TRUE, '{"market_cap_rank": 50, "tags": ["trading", "cosmos"]}'),
    ('TIA', 'Celestia', 'Data Availability', TRUE, '{"market_cap_rank": 45, "tags": ["modular", "data-availability"]}'),
    ('ATOM', 'Cosmos', 'Layer 0', TRUE, '{"market_cap_rank": 25, "tags": ["interoperability", "ibc"]}'),
    ('NEAR', 'NEAR Protocol', 'Layer 1', TRUE, '{"market_cap_rank": 24, "tags": ["sharding", "web3"]}')
ON CONFLICT (symbol) DO UPDATE
SET
    name = EXCLUDED.name,
    category = EXCLUDED.category,
    metadata = EXCLUDED.metadata,
    updated_at = NOW();

-- ============================================================================
-- SEED SYSTEM METRICS
-- ============================================================================

-- Initial system metrics for monitoring
INSERT INTO system_metrics (metric_type, metric_name, metric_value, metric_unit, timeframe, metadata) VALUES
    ('system', 'database_initialized', 1, 'boolean', 'all_time', '{"initialized_at": "2024-01-01"}'),
    ('threshold', 'arbitrage_alert_threshold', 1.0, 'percentage', 'current', '{"description": "Minimum arbitrage percentage for alerts"}'),
    ('threshold', 'data_retention_days', 30, 'days', 'current', '{"description": "Days of historical data to keep"}'),
    ('threshold', 'batch_insert_size', 50, 'count', 'current', '{"description": "Number of records per batch insert"}'),
    ('performance', 'target_scrape_duration', 60, 'seconds', 'current', '{"description": "Target duration for scraping operation"}'),
    ('performance', 'max_retry_attempts', 3, 'count', 'current', '{"description": "Maximum retry attempts for failed operations"}');

-- ============================================================================
-- SCHEDULED JOBS NOTE
-- ============================================================================

-- Note: For Supabase, you'll need to set up scheduled jobs as Edge Functions or external cron jobs
-- Example scheduled jobs you might want to create:
--
-- 1. Refresh materialized views every hour
--    Command: REFRESH MATERIALIZED VIEW CONCURRENTLY mv_latest_funding_rates;
--             REFRESH MATERIALIZED VIEW CONCURRENTLY mv_hourly_stats;
--             REFRESH MATERIALIZED VIEW CONCURRENTLY mv_top_movers;
--
-- 2. Clean up old data weekly (Every Sunday at midnight)
--    Command: CALL cleanup_old_data(30);
--
-- 3. Update coin metadata daily (Every day at 2 AM)
--    Command: CALL update_coin_metadata();
--
-- 4. Generate arbitrage alerts every 5 minutes
--    Command: CALL generate_arbitrage_alerts(1.0);

-- ============================================================================
-- GRANT PERMISSIONS
-- ============================================================================

-- Grant appropriate permissions to application user
-- Note: Adjust the username based on your setup

/*
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO app_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO app_user;
GRANT EXECUTE ON ALL PROCEDURES IN SCHEMA public TO app_user;
*/

-- ============================================================================
-- CREATE TEST DATA (OPTIONAL - Remove in production)
-- ============================================================================

-- Uncomment to create sample funding rate data for testing
/*
INSERT INTO funding_rates (
    coin, hyperliquid_oi, hyperliquid_funding, hyperliquid_sentiment,
    binance_funding, bybit_funding, binance_hl_arb, bybit_hl_arb,
    timeframe, rank_by_oi, scraped_at
)
SELECT
    c.symbol,
    (RANDOM() * 10000000)::DECIMAL(20, 2), -- Random OI between 0-10M
    (RANDOM() * 0.01 - 0.005)::DECIMAL(10, 6), -- Random funding -0.005% to 0.005%
    CASE
        WHEN RANDOM() < 0.33 THEN 'positive'
        WHEN RANDOM() < 0.66 THEN 'negative'
        ELSE 'neutral'
    END,
    (RANDOM() * 0.01 - 0.005)::DECIMAL(10, 6), -- Random Binance funding
    (RANDOM() * 0.01 - 0.005)::DECIMAL(10, 6), -- Random Bybit funding
    (RANDOM() * 0.002 - 0.001)::DECIMAL(10, 6), -- Random arbitrage
    (RANDOM() * 0.002 - 0.001)::DECIMAL(10, 6), -- Random arbitrage
    'hourly',
    ROW_NUMBER() OVER (ORDER BY RANDOM()),
    NOW() - INTERVAL '1 hour'
FROM coins c
WHERE c.is_active = TRUE;
*/

-- ============================================================================
-- RECORD MIGRATION
-- ============================================================================

INSERT INTO migrations (version, name, description, checksum)
VALUES (
    4,
    '004_seed_data',
    'Initial seed data and configuration',
    MD5('004_seed_data_v1')
) ON CONFLICT (version) DO NOTHING;