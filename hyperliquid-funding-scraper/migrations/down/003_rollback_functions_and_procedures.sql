-- Rollback Migration: 003_functions_and_procedures
-- Description: Rollback database functions, procedures, and views
-- Date: 2024-01-03
-- Author: Hyperliquid Scraper System

-- ============================================================================
-- DROP VIEWS
-- ============================================================================

DROP VIEW IF EXISTS v_coin_leaderboard CASCADE;
DROP VIEW IF EXISTS v_dashboard_stats CASCADE;

-- ============================================================================
-- DROP AGGREGATE FUNCTIONS
-- ============================================================================

DROP AGGREGATE IF EXISTS weighted_avg(NUMERIC, NUMERIC);
DROP FUNCTION IF EXISTS weighted_avg_final(NUMERIC[]);
DROP FUNCTION IF EXISTS weighted_avg_state(NUMERIC[], NUMERIC, NUMERIC);

-- ============================================================================
-- DROP STORED PROCEDURES
-- ============================================================================

DROP PROCEDURE IF EXISTS generate_arbitrage_alerts(DECIMAL);
DROP PROCEDURE IF EXISTS update_coin_metadata();
DROP PROCEDURE IF EXISTS cleanup_old_data(INTEGER);

-- ============================================================================
-- DROP FUNCTIONS
-- ============================================================================

DROP FUNCTION IF EXISTS get_top_movers(INTEGER, VARCHAR, VARCHAR);
DROP FUNCTION IF EXISTS find_arbitrage_opportunities(DECIMAL, VARCHAR);
DROP FUNCTION IF EXISTS get_coin_stats(VARCHAR, VARCHAR, INTEGER);

-- ============================================================================
-- UPDATE MIGRATION LOG
-- ============================================================================

UPDATE migrations
SET rollback_executed = TRUE,
    rollback_at = NOW()
WHERE version = 3;