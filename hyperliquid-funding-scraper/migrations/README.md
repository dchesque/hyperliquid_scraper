# Database Migrations

Complete migration system for the Hyperliquid Funding Scraper database.

## Overview

This directory contains all database migrations for setting up and maintaining the Supabase PostgreSQL database. The migration system supports both forward migrations (up) and rollbacks (down).

## Migration Structure

```
migrations/
├── 001_initial_schema.sql       # Core tables and basic indexes
├── 002_performance_indexes.sql  # Performance optimizations
├── 003_functions_and_procedures.sql  # Business logic
├── 004_seed_data.sql            # Initial data
├── down/                        # Rollback scripts
│   ├── 001_rollback_initial_schema.sql
│   ├── 002_rollback_performance_indexes.sql
│   └── 003_rollback_functions_and_procedures.sql
└── migrate.py                   # Migration runner
```

## Quick Start

### Method 1: Using Supabase Dashboard (Recommended)

1. Open your Supabase project dashboard
2. Navigate to SQL Editor
3. Run each migration file in order:
   - `001_initial_schema.sql`
   - `002_performance_indexes.sql`
   - `003_functions_and_procedures.sql`
   - `004_seed_data.sql`

### Method 2: Using Migration Runner

1. Install dependencies:
```bash
pip install psycopg2-binary
```

2. Set environment variable:
```bash
export SUPABASE_DB_PASSWORD=your_db_password
```

3. Run migrations:
```bash
# Check status
python migrations/migrate.py status

# Run all migrations
python migrations/migrate.py up

# Run up to specific version
python migrations/migrate.py up --version 2

# Rollback to version
python migrations/migrate.py down --version 1
```

### Method 3: Using psql

```bash
# Connect to database
psql postgresql://postgres:password@db.project.supabase.co:5432/postgres

# Run migrations
\i migrations/001_initial_schema.sql
\i migrations/002_performance_indexes.sql
\i migrations/003_functions_and_procedures.sql
\i migrations/004_seed_data.sql
```

## Migration Details

### 001 - Initial Schema
Creates the core database structure:
- `funding_rates` - Main data table for funding rates
- `scraping_logs` - Scraping operation logs
- `coins` - Cryptocurrency metadata
- `arbitrage_alerts` - Arbitrage opportunity tracking
- `system_metrics` - System monitoring data
- `migrations` - Migration tracking table

### 002 - Performance Indexes
Adds performance optimizations:
- Composite indexes for common queries
- Partial indexes for filtered searches
- Materialized views for analytics:
  - `mv_latest_funding_rates` - Latest rates per coin
  - `mv_hourly_stats` - Hourly statistics
  - `mv_top_movers` - Top gainers/losers

### 003 - Functions and Procedures
Implements business logic:
- **Functions:**
  - `get_coin_stats()` - Get statistics for a specific coin
  - `find_arbitrage_opportunities()` - Find arbitrage opportunities
  - `get_top_movers()` - Get top moving coins
- **Procedures:**
  - `cleanup_old_data()` - Clean up old records
  - `update_coin_metadata()` - Update coin information
  - `generate_arbitrage_alerts()` - Generate alerts
- **Views:**
  - `v_dashboard_stats` - Real-time dashboard statistics
  - `v_coin_leaderboard` - Coin rankings

### 004 - Seed Data
Loads initial configuration:
- Popular cryptocurrency metadata
- System configuration metrics
- Default thresholds and settings

## Database Schema

### Key Tables

#### funding_rates
| Column | Type | Description |
|--------|------|-------------|
| id | BIGSERIAL | Primary key |
| coin | VARCHAR(20) | Cryptocurrency symbol |
| hyperliquid_oi | DECIMAL(20,2) | Open Interest (USD) |
| hyperliquid_funding | DECIMAL(10,6) | Funding rate (%) |
| hyperliquid_sentiment | VARCHAR(10) | Market sentiment |
| binance_funding | DECIMAL(10,6) | Binance funding rate |
| bybit_funding | DECIMAL(10,6) | Bybit funding rate |
| binance_hl_arb | DECIMAL(10,6) | Binance arbitrage |
| bybit_hl_arb | DECIMAL(10,6) | Bybit arbitrage |
| timeframe | VARCHAR(10) | Data timeframe |
| scraped_at | TIMESTAMP | Scraping time |

#### scraping_logs
| Column | Type | Description |
|--------|------|-------------|
| id | BIGSERIAL | Primary key |
| status | VARCHAR(20) | Operation status |
| coins_scraped | INTEGER | Number of coins |
| duration_seconds | DECIMAL(10,2) | Operation duration |
| error_message | TEXT | Error details |
| created_at | TIMESTAMP | Log timestamp |

## Maintenance

### Refresh Materialized Views
```sql
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_latest_funding_rates;
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_hourly_stats;
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_top_movers;
```

### Clean Old Data
```sql
CALL cleanup_old_data(30); -- Keep 30 days
```

### Update Coin Metadata
```sql
CALL update_coin_metadata();
```

### Generate Arbitrage Alerts
```sql
CALL generate_arbitrage_alerts(1.0); -- 1% threshold
```

## Backup and Recovery

### Create Backup
```bash
pg_dump postgresql://user:pass@host:5432/db > backup.sql
```

### Restore from Backup
```bash
psql postgresql://user:pass@host:5432/db < backup.sql
```

## Performance Tips

1. **Regular Maintenance:**
   - Run `VACUUM ANALYZE` weekly
   - Refresh materialized views hourly
   - Clean old data monthly

2. **Index Usage:**
   - Monitor with `pg_stat_user_indexes`
   - Add indexes for frequent query patterns
   - Remove unused indexes

3. **Query Optimization:**
   - Use materialized views for analytics
   - Leverage partial indexes
   - Batch inserts for better performance

## Troubleshooting

### Migration Failed
1. Check error message in logs
2. Verify database connectivity
3. Ensure proper permissions
4. Rollback if needed: `python migrate.py down --version X`

### Slow Queries
1. Check query execution plan: `EXPLAIN ANALYZE query`
2. Verify indexes are being used
3. Consider refreshing materialized views
4. Run `VACUUM ANALYZE` on affected tables

### Connection Issues
1. Verify Supabase URL and credentials
2. Check network connectivity
3. Ensure SSL mode is correct
4. Verify database is not in maintenance

## Creating New Migrations

```bash
# Create new migration files
python migrations/migrate.py create --name my_new_feature

# This creates:
# - migrations/005_my_new_feature.sql
# - migrations/down/005_rollback_my_new_feature.sql
```

## Security Considerations

1. **Never commit passwords** to version control
2. Use environment variables for credentials
3. Grant minimal required permissions
4. Enable Row Level Security (RLS) where appropriate
5. Audit sensitive operations

## Support

For issues with migrations:
1. Check migration logs in `migrations` table
2. Review Supabase dashboard logs
3. Consult PostgreSQL documentation
4. Open an issue on GitHub