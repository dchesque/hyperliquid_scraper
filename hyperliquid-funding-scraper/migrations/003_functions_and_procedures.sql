-- Migration: 003_functions_and_procedures
-- Description: Database functions and stored procedures for business logic
-- Date: 2024-01-03
-- Author: Hyperliquid Scraper System

-- ============================================================================
-- UTILITY FUNCTIONS
-- ============================================================================

-- Function to calculate funding rate statistics for a coin
CREATE OR REPLACE FUNCTION get_coin_stats(
    p_coin VARCHAR,
    p_timeframe VARCHAR DEFAULT 'hourly',
    p_hours INTEGER DEFAULT 24
)
RETURNS TABLE(
    coin VARCHAR,
    timeframe VARCHAR,
    data_points BIGINT,
    avg_funding DECIMAL,
    max_funding DECIMAL,
    min_funding DECIMAL,
    std_dev_funding DECIMAL,
    current_funding DECIMAL,
    current_oi DECIMAL,
    total_arbitrage_opportunities BIGINT,
    last_updated TIMESTAMP WITH TIME ZONE
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    WITH recent_data AS (
        SELECT
            fr.coin,
            fr.timeframe,
            fr.hyperliquid_funding,
            fr.hyperliquid_oi,
            fr.binance_hl_arb,
            fr.bybit_hl_arb,
            fr.scraped_at
        FROM funding_rates fr
        WHERE fr.coin = p_coin
            AND fr.timeframe = p_timeframe
            AND fr.scraped_at >= NOW() - (p_hours || ' hours')::INTERVAL
        ORDER BY fr.scraped_at DESC
    )
    SELECT
        rd.coin,
        rd.timeframe,
        COUNT(*) as data_points,
        AVG(rd.hyperliquid_funding) as avg_funding,
        MAX(rd.hyperliquid_funding) as max_funding,
        MIN(rd.hyperliquid_funding) as min_funding,
        STDDEV(rd.hyperliquid_funding) as std_dev_funding,
        FIRST_VALUE(rd.hyperliquid_funding) OVER (ORDER BY rd.scraped_at DESC) as current_funding,
        FIRST_VALUE(rd.hyperliquid_oi) OVER (ORDER BY rd.scraped_at DESC) as current_oi,
        COUNT(*) FILTER (
            WHERE ABS(COALESCE(rd.binance_hl_arb, 0)) > 1
                OR ABS(COALESCE(rd.bybit_hl_arb, 0)) > 1
        ) as total_arbitrage_opportunities,
        MAX(rd.scraped_at) as last_updated
    FROM recent_data rd
    GROUP BY rd.coin, rd.timeframe;
END;
$$;

-- Function to find arbitrage opportunities
CREATE OR REPLACE FUNCTION find_arbitrage_opportunities(
    p_threshold DECIMAL DEFAULT 1.0,
    p_timeframe VARCHAR DEFAULT NULL
)
RETURNS TABLE(
    coin VARCHAR,
    exchange VARCHAR,
    hyperliquid_funding DECIMAL,
    exchange_funding DECIMAL,
    arbitrage_value DECIMAL,
    timeframe VARCHAR,
    scraped_at TIMESTAMP WITH TIME ZONE
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    WITH latest_rates AS (
        SELECT DISTINCT ON (fr.coin, fr.timeframe)
            fr.*
        FROM funding_rates fr
        WHERE (p_timeframe IS NULL OR fr.timeframe = p_timeframe)
            AND fr.scraped_at >= NOW() - INTERVAL '1 hour'
        ORDER BY fr.coin, fr.timeframe, fr.scraped_at DESC
    )
    SELECT
        lr.coin,
        'Binance'::VARCHAR as exchange,
        lr.hyperliquid_funding,
        lr.binance_funding as exchange_funding,
        lr.binance_hl_arb as arbitrage_value,
        lr.timeframe,
        lr.scraped_at
    FROM latest_rates lr
    WHERE ABS(COALESCE(lr.binance_hl_arb, 0)) >= p_threshold

    UNION ALL

    SELECT
        lr.coin,
        'Bybit'::VARCHAR as exchange,
        lr.hyperliquid_funding,
        lr.bybit_funding as exchange_funding,
        lr.bybit_hl_arb as arbitrage_value,
        lr.timeframe,
        lr.scraped_at
    FROM latest_rates lr
    WHERE ABS(COALESCE(lr.bybit_hl_arb, 0)) >= p_threshold

    ORDER BY arbitrage_value DESC;
END;
$$;

-- Function to get top movers
CREATE OR REPLACE FUNCTION get_top_movers(
    p_limit INTEGER DEFAULT 10,
    p_direction VARCHAR DEFAULT 'both', -- 'positive', 'negative', 'both'
    p_timeframe VARCHAR DEFAULT 'hourly'
)
RETURNS TABLE(
    coin VARCHAR,
    current_funding DECIMAL,
    previous_funding DECIMAL,
    funding_change DECIMAL,
    change_percentage DECIMAL,
    current_oi DECIMAL,
    timeframe VARCHAR
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    WITH current_snapshot AS (
        SELECT DISTINCT ON (fr.coin)
            fr.coin,
            fr.hyperliquid_funding,
            fr.hyperliquid_oi,
            fr.timeframe,
            fr.scraped_at
        FROM funding_rates fr
        WHERE fr.timeframe = p_timeframe
            AND fr.scraped_at >= NOW() - INTERVAL '1 hour'
        ORDER BY fr.coin, fr.scraped_at DESC
    ),
    previous_snapshot AS (
        SELECT DISTINCT ON (fr.coin)
            fr.coin,
            fr.hyperliquid_funding as prev_funding
        FROM funding_rates fr
        WHERE fr.timeframe = p_timeframe
            AND fr.scraped_at >= NOW() - INTERVAL '25 hours'
            AND fr.scraped_at < NOW() - INTERVAL '23 hours'
        ORDER BY fr.coin, fr.scraped_at DESC
    )
    SELECT
        cs.coin,
        cs.hyperliquid_funding as current_funding,
        ps.prev_funding as previous_funding,
        (cs.hyperliquid_funding - COALESCE(ps.prev_funding, 0)) as funding_change,
        CASE
            WHEN ps.prev_funding IS NOT NULL AND ps.prev_funding != 0
            THEN ((cs.hyperliquid_funding - ps.prev_funding) / ABS(ps.prev_funding) * 100)
            ELSE 0
        END as change_percentage,
        cs.hyperliquid_oi as current_oi,
        cs.timeframe
    FROM current_snapshot cs
    LEFT JOIN previous_snapshot ps ON cs.coin = ps.coin
    WHERE cs.hyperliquid_funding IS NOT NULL
        AND (
            p_direction = 'both'
            OR (p_direction = 'positive' AND cs.hyperliquid_funding > COALESCE(ps.prev_funding, 0))
            OR (p_direction = 'negative' AND cs.hyperliquid_funding < COALESCE(ps.prev_funding, 0))
        )
    ORDER BY ABS(cs.hyperliquid_funding - COALESCE(ps.prev_funding, 0)) DESC
    LIMIT p_limit;
END;
$$;

-- ============================================================================
-- STORED PROCEDURES
-- ============================================================================

-- Procedure to clean old data
CREATE OR REPLACE PROCEDURE cleanup_old_data(
    p_days_to_keep INTEGER DEFAULT 30
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_deleted_count INTEGER;
BEGIN
    -- Delete old funding rates
    DELETE FROM funding_rates
    WHERE scraped_at < NOW() - (p_days_to_keep || ' days')::INTERVAL;

    GET DIAGNOSTICS v_deleted_count = ROW_COUNT;
    RAISE NOTICE 'Deleted % old funding rate records', v_deleted_count;

    -- Delete old scraping logs
    DELETE FROM scraping_logs
    WHERE created_at < NOW() - (p_days_to_keep || ' days')::INTERVAL;

    GET DIAGNOSTICS v_deleted_count = ROW_COUNT;
    RAISE NOTICE 'Deleted % old scraping log records', v_deleted_count;

    -- Delete old system metrics
    DELETE FROM system_metrics
    WHERE created_at < NOW() - (p_days_to_keep || ' days')::INTERVAL;

    GET DIAGNOSTICS v_deleted_count = ROW_COUNT;
    RAISE NOTICE 'Deleted % old system metric records', v_deleted_count;

    -- Vacuum analyze tables
    VACUUM ANALYZE funding_rates;
    VACUUM ANALYZE scraping_logs;
    VACUUM ANALYZE system_metrics;

    RAISE NOTICE 'Cleanup completed successfully';
END;
$$;

-- Procedure to update coin metadata
CREATE OR REPLACE PROCEDURE update_coin_metadata()
LANGUAGE plpgsql
AS $$
BEGIN
    -- Insert new coins or update existing ones
    INSERT INTO coins (symbol, last_seen_at, total_scrapes)
    SELECT
        coin,
        MAX(scraped_at),
        COUNT(*)
    FROM funding_rates
    WHERE scraped_at >= NOW() - INTERVAL '24 hours'
    GROUP BY coin
    ON CONFLICT (symbol) DO UPDATE
    SET
        last_seen_at = EXCLUDED.last_seen_at,
        total_scrapes = coins.total_scrapes + EXCLUDED.total_scrapes,
        updated_at = NOW();

    -- Mark coins as inactive if not seen in 7 days
    UPDATE coins
    SET is_active = FALSE
    WHERE last_seen_at < NOW() - INTERVAL '7 days'
        AND is_active = TRUE;

    RAISE NOTICE 'Coin metadata updated successfully';
END;
$$;

-- Procedure to generate arbitrage alerts
CREATE OR REPLACE PROCEDURE generate_arbitrage_alerts(
    p_threshold DECIMAL DEFAULT 1.0
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_alert_count INTEGER := 0;
BEGIN
    -- Insert new arbitrage alerts
    INSERT INTO arbitrage_alerts (
        coin,
        exchange,
        hyperliquid_funding,
        exchange_funding,
        arbitrage_value,
        timeframe,
        alert_threshold,
        funding_rate_id
    )
    SELECT
        fr.coin,
        CASE
            WHEN ABS(COALESCE(fr.binance_hl_arb, 0)) > ABS(COALESCE(fr.bybit_hl_arb, 0))
            THEN 'Binance'
            ELSE 'Bybit'
        END as exchange,
        fr.hyperliquid_funding,
        CASE
            WHEN ABS(COALESCE(fr.binance_hl_arb, 0)) > ABS(COALESCE(fr.bybit_hl_arb, 0))
            THEN fr.binance_funding
            ELSE fr.bybit_funding
        END as exchange_funding,
        CASE
            WHEN ABS(COALESCE(fr.binance_hl_arb, 0)) > ABS(COALESCE(fr.bybit_hl_arb, 0))
            THEN fr.binance_hl_arb
            ELSE fr.bybit_hl_arb
        END as arbitrage_value,
        fr.timeframe,
        p_threshold,
        fr.id
    FROM funding_rates fr
    WHERE fr.scraped_at >= NOW() - INTERVAL '1 hour'
        AND (
            ABS(COALESCE(fr.binance_hl_arb, 0)) >= p_threshold
            OR ABS(COALESCE(fr.bybit_hl_arb, 0)) >= p_threshold
        )
        AND NOT EXISTS (
            SELECT 1
            FROM arbitrage_alerts aa
            WHERE aa.funding_rate_id = fr.id
        );

    GET DIAGNOSTICS v_alert_count = ROW_COUNT;
    RAISE NOTICE 'Generated % new arbitrage alerts', v_alert_count;
END;
$$;

-- ============================================================================
-- AGGREGATE FUNCTIONS
-- ============================================================================

-- Custom aggregate for weighted average
CREATE OR REPLACE FUNCTION weighted_avg_state(
    state NUMERIC[],
    value NUMERIC,
    weight NUMERIC
)
RETURNS NUMERIC[]
LANGUAGE plpgsql
AS $$
BEGIN
    IF state IS NULL THEN
        RETURN ARRAY[value * weight, weight];
    ELSE
        RETURN ARRAY[state[1] + (value * weight), state[2] + weight];
    END IF;
END;
$$;

CREATE OR REPLACE FUNCTION weighted_avg_final(state NUMERIC[])
RETURNS NUMERIC
LANGUAGE plpgsql
AS $$
BEGIN
    IF state IS NULL OR state[2] = 0 THEN
        RETURN NULL;
    ELSE
        RETURN state[1] / state[2];
    END IF;
END;
$$;

-- Drop aggregate if exists (for idempotency)
DROP AGGREGATE IF EXISTS weighted_avg(NUMERIC, NUMERIC);

-- Create weighted average aggregate
CREATE AGGREGATE weighted_avg(NUMERIC, NUMERIC) (
    SFUNC = weighted_avg_state,
    STYPE = NUMERIC[],
    FINALFUNC = weighted_avg_final
);

-- ============================================================================
-- VIEWS
-- ============================================================================

-- Real-time dashboard view
CREATE OR REPLACE VIEW v_dashboard_stats AS
WITH latest_scrape AS (
    SELECT MAX(scraped_at) as last_scrape_time
    FROM funding_rates
    WHERE scraped_at >= NOW() - INTERVAL '2 hours'
),
recent_rates AS (
    SELECT *
    FROM funding_rates
    WHERE scraped_at = (SELECT last_scrape_time FROM latest_scrape)
)
SELECT
    (SELECT last_scrape_time FROM latest_scrape) as last_update,
    COUNT(DISTINCT coin) as total_coins,
    COUNT(*) FILTER (WHERE hyperliquid_funding > 0) as positive_funding,
    COUNT(*) FILTER (WHERE hyperliquid_funding < 0) as negative_funding,
    COUNT(*) FILTER (WHERE hyperliquid_funding = 0 OR hyperliquid_funding IS NULL) as neutral_funding,
    COALESCE(AVG(hyperliquid_funding), 0) as avg_funding,
    COALESCE(SUM(hyperliquid_oi), 0) as total_open_interest,
    COUNT(*) FILTER (
        WHERE ABS(COALESCE(binance_hl_arb, 0)) > 1
            OR ABS(COALESCE(bybit_hl_arb, 0)) > 1
    ) as arbitrage_opportunities
FROM recent_rates;

-- Coin leaderboard view
CREATE OR REPLACE VIEW v_coin_leaderboard AS
WITH latest_data AS (
    SELECT DISTINCT ON (coin, timeframe)
        coin,
        timeframe,
        hyperliquid_oi,
        hyperliquid_funding,
        rank_by_oi
    FROM funding_rates
    WHERE scraped_at >= NOW() - INTERVAL '1 hour'
    ORDER BY coin, timeframe, scraped_at DESC
)
SELECT
    coin,
    timeframe,
    hyperliquid_oi,
    hyperliquid_funding,
    rank_by_oi,
    RANK() OVER (PARTITION BY timeframe ORDER BY hyperliquid_oi DESC NULLS LAST) as oi_rank,
    RANK() OVER (PARTITION BY timeframe ORDER BY hyperliquid_funding DESC NULLS LAST) as funding_rank
FROM latest_data
ORDER BY timeframe, hyperliquid_oi DESC NULLS LAST;

-- ============================================================================
-- RECORD MIGRATION
-- ============================================================================

INSERT INTO migrations (version, name, description, checksum)
VALUES (
    3,
    '003_functions_and_procedures',
    'Database functions, stored procedures, and views for business logic',
    MD5('003_functions_and_procedures_v1')
) ON CONFLICT (version) DO NOTHING;