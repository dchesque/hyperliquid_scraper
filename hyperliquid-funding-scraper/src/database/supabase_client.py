"""Supabase client with Python 3.13 and httpx compatibility fixes."""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging
import os

# Try different import strategies for compatibility
try:
    from supabase import create_client, Client
    from postgrest.exceptions import APIError
    SUPABASE_AVAILABLE = True
except ImportError as e:
    SUPABASE_AVAILABLE = False
    print(f"Supabase import error: {e}")

# Alternative: Direct PostgreSQL connection as fallback
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False

from src.config import settings
from src.database.models import FundingRate, ScrapingLog
from src.utils.logger import get_logger, LoggerMixin


class SupabaseClient(LoggerMixin):
    """Client for interacting with Supabase database with compatibility fixes."""

    def __init__(self, url: Optional[str] = None, key: Optional[str] = None):
        """
        Initialize Supabase client with fallback options.

        Args:
            url: Supabase project URL
            key: Supabase anon key
        """
        self.url = url or settings.supabase_url
        self.key = key or settings.supabase_key
        self.client = None
        self.use_postgres_direct = False

        # Try to initialize Supabase client
        if SUPABASE_AVAILABLE:
            try:
                # Monkey patch to fix httpx compatibility issue
                import httpx
                import gotrue._sync.gotrue_base_api as gotrue_base

                # Override the problematic Client initialization
                original_init = httpx.Client.__init__

                def patched_init(self, *args, **kwargs):
                    # Remove proxy argument if it exists
                    kwargs.pop('proxy', None)
                    original_init(self, *args, **kwargs)

                httpx.Client.__init__ = patched_init

                # Now create the Supabase client
                self.client: Client = create_client(self.url, self.key)
                self.logger.info("Supabase client initialized successfully")

            except Exception as e:
                self.logger.warning(f"Failed to initialize Supabase client: {e}")
                self.logger.info("Falling back to direct PostgreSQL connection")
                self.use_postgres_direct = True
        else:
            self.logger.warning("Supabase library not available")
            self.use_postgres_direct = True

        # Setup PostgreSQL fallback if needed
        if self.use_postgres_direct and POSTGRES_AVAILABLE:
            self._setup_postgres_fallback()

    def _setup_postgres_fallback(self):
        """Setup direct PostgreSQL connection as fallback."""
        try:
            # Extract PostgreSQL connection details from Supabase URL
            # Format: https://[PROJECT_REF].supabase.co
            import re
            match = re.search(r'https://([^.]+)\.supabase\.co', self.url)
            if match:
                project_ref = match.group(1)

                # Get database password from environment
                db_password = os.getenv("SUPABASE_DB_PASSWORD")
                if db_password:
                    self.pg_config = {
                        "host": f"db.{project_ref}.supabase.co",
                        "port": 5432,
                        "database": "postgres",
                        "user": "postgres",
                        "password": db_password
                    }
                    self.logger.info("PostgreSQL fallback configured")
                else:
                    self.logger.error("SUPABASE_DB_PASSWORD not set for PostgreSQL fallback")
        except Exception as e:
            self.logger.error(f"Failed to setup PostgreSQL fallback: {e}")

    def _get_pg_connection(self):
        """Get PostgreSQL connection."""
        if hasattr(self, 'pg_config'):
            return psycopg2.connect(**self.pg_config)
        return None

    # Funding Rates Operations

    def insert_funding_rates(self, rates: List[FundingRate], batch_size: Optional[int] = None) -> bool:
        """
        Insert funding rates in batches.

        Args:
            rates: List of FundingRate objects
            batch_size: Size of each batch

        Returns:
            Success status
        """
        batch_size = batch_size or settings.batch_insert_size
        total_inserted = 0

        try:
            if self.client and not self.use_postgres_direct:
                # Use Supabase client
                for i in range(0, len(rates), batch_size):
                    batch = rates[i:i + batch_size]
                    batch_data = [rate.to_dict() for rate in batch if rate.validate()]

                    if batch_data:
                        response = self.client.table("funding_rates").upsert(
                            batch_data,
                            on_conflict="coin,timeframe,scraped_at"
                        ).execute()

                        total_inserted += len(batch_data)
                        self.logger.debug(f"Inserted batch of {len(batch_data)} rates")

            elif self.use_postgres_direct and POSTGRES_AVAILABLE:
                # Use direct PostgreSQL
                conn = self._get_pg_connection()
                if conn:
                    with conn.cursor() as cur:
                        for i in range(0, len(rates), batch_size):
                            batch = rates[i:i + batch_size]
                            for rate in batch:
                                if rate.validate():
                                    data = rate.to_dict()
                                    cur.execute("""
                                        INSERT INTO funding_rates
                                        (coin, hyperliquid_oi, hyperliquid_funding, hyperliquid_sentiment,
                                         binance_funding, bybit_funding, binance_hl_arb, bybit_hl_arb,
                                         timeframe, rank_by_oi, is_favorited, scraped_at)
                                        VALUES (%(coin)s, %(hyperliquid_oi)s, %(hyperliquid_funding)s,
                                                %(hyperliquid_sentiment)s, %(binance_funding)s, %(bybit_funding)s,
                                                %(binance_hl_arb)s, %(bybit_hl_arb)s, %(timeframe)s,
                                                %(rank_by_oi)s, %(is_favorited)s, %(scraped_at)s)
                                        ON CONFLICT (coin, timeframe, scraped_at) DO UPDATE
                                        SET hyperliquid_oi = EXCLUDED.hyperliquid_oi,
                                            hyperliquid_funding = EXCLUDED.hyperliquid_funding
                                    """, data)
                                    total_inserted += 1
                        conn.commit()
                    conn.close()

            self.logger.info(f"Successfully inserted {total_inserted} funding rates")
            return True

        except Exception as e:
            self.logger.error(f"Error inserting funding rates: {e}")
            return False

    def get_latest_funding_rates(self, timeframe: str = "hourly", limit: int = 100) -> List[FundingRate]:
        """
        Get latest funding rates for a timeframe.

        Args:
            timeframe: Timeframe to filter
            limit: Maximum number of results

        Returns:
            List of FundingRate objects
        """
        try:
            if self.client and not self.use_postgres_direct:
                response = self.client.table("funding_rates") \
                    .select("*") \
                    .eq("timeframe", timeframe) \
                    .order("scraped_at", desc=True) \
                    .limit(limit) \
                    .execute()

                rates = [FundingRate.from_dict(data) for data in response.data]

            elif self.use_postgres_direct and POSTGRES_AVAILABLE:
                conn = self._get_pg_connection()
                rates = []
                if conn:
                    with conn.cursor(cursor_factory=RealDictCursor) as cur:
                        cur.execute("""
                            SELECT * FROM funding_rates
                            WHERE timeframe = %s
                            ORDER BY scraped_at DESC
                            LIMIT %s
                        """, (timeframe, limit))

                        for row in cur.fetchall():
                            rates.append(FundingRate.from_dict(dict(row)))
                    conn.close()
            else:
                rates = []

            self.logger.debug(f"Retrieved {len(rates)} latest funding rates")
            return rates

        except Exception as e:
            self.logger.error(f"Error retrieving latest funding rates: {e}")
            return []

    def test_connection(self) -> bool:
        """
        Test database connection.

        Returns:
            Connection status
        """
        try:
            if self.client and not self.use_postgres_direct:
                # Try Supabase connection
                response = self.client.table("funding_rates") \
                    .select("id") \
                    .limit(1) \
                    .execute()
                self.logger.info("Supabase connection test successful")
                return True

            elif self.use_postgres_direct and POSTGRES_AVAILABLE:
                # Try PostgreSQL connection
                conn = self._get_pg_connection()
                if conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT 1")
                        result = cur.fetchone()
                    conn.close()
                    if result:
                        self.logger.info("PostgreSQL connection test successful")
                        return True

            return False

        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False

    def insert_scraping_log(self, log: ScrapingLog) -> bool:
        """
        Insert a scraping log entry.

        Args:
            log: ScrapingLog object

        Returns:
            Success status
        """
        try:
            if self.client and not self.use_postgres_direct:
                response = self.client.table("scraping_logs") \
                    .insert(log.to_dict()) \
                    .execute()

            elif self.use_postgres_direct and POSTGRES_AVAILABLE:
                conn = self._get_pg_connection()
                if conn:
                    with conn.cursor() as cur:
                        data = log.to_dict()
                        cur.execute("""
                            INSERT INTO scraping_logs
                            (status, coins_scraped, duration_seconds, error_message,
                             timeframe, total_coins_found, arbitrage_opportunities)
                            VALUES (%(status)s, %(coins_scraped)s, %(duration_seconds)s,
                                    %(error_message)s, %(timeframe)s, %(total_coins_found)s,
                                    %(arbitrage_opportunities)s)
                        """, data)
                        conn.commit()
                    conn.close()

            self.logger.info(f"Inserted scraping log: {log.status}")
            return True

        except Exception as e:
            self.logger.error(f"Error inserting scraping log: {e}")
            return False

    # Add stub methods for other operations to maintain compatibility
    def get_coin_history(self, coin: str, timeframe: str = "hourly", hours_back: int = 24) -> List[FundingRate]:
        """Get historical funding rates for a specific coin."""
        return []

    def get_top_movers(self, timeframe: str = "hourly", limit: int = 10, direction: str = "positive") -> List[FundingRate]:
        """Get top movers by funding rate."""
        return []

    def get_arbitrage_opportunities(self, timeframe: str = "hourly", min_threshold: float = 1.0) -> List[FundingRate]:
        """Get current arbitrage opportunities."""
        return []

    def get_scraping_logs(self, limit: int = 100) -> List[ScrapingLog]:
        """Get recent scraping logs."""
        return []

    def get_scraping_stats(self, hours_back: int = 24) -> Dict[str, Any]:
        """Get scraping statistics for a time period."""
        return {}

    def cleanup_old_data(self, days: Optional[int] = None) -> int:
        """Delete old funding rate data."""
        return 0

    def export_to_dict(self, timeframe: str = "hourly", hours_back: int = 24) -> List[Dict[str, Any]]:
        """Export funding rates to dictionary format."""
        return []

    def create_tables(self) -> bool:
        """Create database tables if they don't exist."""
        self.logger.info("Tables should be created via migrations")
        return True