"""Main application entry point for Hyperliquid Funding Scraper."""

import sys
import time
import signal
import click
import schedule
import threading
import json
from typing import Optional, List
from datetime import datetime, timedelta
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

from src.config import settings
from src.utils.logger import setup_logging, get_logger, log_scraping_metrics
from src.scrapers import FundingRateScraper
from src.database import SupabaseClient, ScrapingLog
from src.utils import DataProcessor


# Global flag for graceful shutdown
shutdown_flag = False

# Global status for health checks
app_status = {
    "status": "starting",
    "last_scraping": None,
    "last_success": None,
    "database_connected": False,
    "total_scraped": 0,
    "uptime_start": datetime.now().isoformat()
}


class HealthCheckHandler(BaseHTTPRequestHandler):
    """Simple HTTP handler for health checks and status endpoints."""

    def do_GET(self):
        global app_status

        try:
            if self.path == "/health":
                # Basic health check
                status_code = 200 if app_status["database_connected"] else 503
                response = {
                    "status": "healthy" if status_code == 200 else "unhealthy",
                    "timestamp": datetime.now().isoformat(),
                    "database": "connected" if app_status["database_connected"] else "disconnected"
                }

            elif self.path == "/api/status" or self.path == "/status":
                # Detailed status information
                response = dict(app_status)
                response["timestamp"] = datetime.now().isoformat()

                # Calculate uptime
                start_time = datetime.fromisoformat(app_status["uptime_start"])
                uptime = datetime.now() - start_time
                response["uptime_seconds"] = int(uptime.total_seconds())
                response["uptime_hours"] = round(uptime.total_seconds() / 3600, 2)

                status_code = 200

            elif self.path == "/" or self.path == "/api":
                # Root endpoint info
                response = {
                    "service": "Hyperliquid Funding Scraper",
                    "version": "1.0.0",
                    "status": app_status["status"],
                    "endpoints": ["/health", "/api/status", "/api"]
                }
                status_code = 200

            else:
                # 404 for unknown endpoints
                response = {"error": "Not found", "path": self.path}
                status_code = 404

        except Exception as e:
            response = {"error": str(e), "status": "error"}
            status_code = 500

        # Send response
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        response_json = json.dumps(response, indent=2)
        self.wfile.write(response_json.encode())

    def log_message(self, format, *args):
        """Suppress default logging to avoid spam."""
        return


def start_http_server(port: int = 8080):
    """Start HTTP server for health checks."""
    try:
        server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
        logger = get_logger(__name__)
        logger.info(f"HTTP server started on port {port}")
        logger.info(f"Health check: http://localhost:{port}/health")
        logger.info(f"Status API: http://localhost:{port}/api/status")
        server.serve_forever()
    except Exception as e:
        logger = get_logger(__name__)
        logger.error(f"Failed to start HTTP server: {e}")


def update_app_status(status: str = None, database_connected: bool = None,
                     last_scraping: bool = None, scraped_count: int = None):
    """Update global application status."""
    global app_status

    if status:
        app_status["status"] = status
    if database_connected is not None:
        app_status["database_connected"] = database_connected
    if last_scraping:
        app_status["last_scraping"] = datetime.now().isoformat()
        if last_scraping:
            app_status["last_success"] = datetime.now().isoformat()
    if scraped_count:
        app_status["total_scraped"] += scraped_count


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global shutdown_flag
    logger = get_logger(__name__)
    logger.info(f"Received signal {signum}. Initiating graceful shutdown...")
    shutdown_flag = True


def run_scraping_job(
    timeframe: str = "hourly",
    export_csv: bool = False,
    export_json: bool = False
) -> bool:
    """
    Run a single scraping job.

    Args:
        timeframe: Timeframe to scrape
        export_csv: Whether to export to CSV
        export_json: Whether to export to JSON

    Returns:
        Success status
    """
    logger = get_logger(__name__)
    start_time = time.time()
    scraper = None
    status = "failed"
    coins_scraped = 0
    error_message = None
    arbitrage_count = 0

    try:
        logger.info(f"Starting scraping job for timeframe: {timeframe}")

        # Initialize components
        db_client = SupabaseClient()
        processor = DataProcessor()

        # Test database connection
        if not db_client.test_connection():
            update_app_status(database_connected=False)
            raise Exception("Failed to connect to Supabase")

        update_app_status(database_connected=True)

        # Initialize scraper
        scraper = FundingRateScraper(headless=settings.headless_mode)

        # Scrape funding rates
        logger.info(f"Scraping {timeframe} funding rates...")
        rates = scraper.scrape_funding_rates(timeframe)

        if not rates:
            logger.warning("No rates scraped")
            status = "partial"
            update_app_status(last_scraping=False)
        else:
            coins_scraped = len(rates)
            logger.info(f"Scraped {coins_scraped} funding rates")
            update_app_status(last_scraping=True, scraped_count=coins_scraped)

            # Validate data quality
            is_valid, errors = processor.validate_data_quality(rates)
            if not is_valid:
                logger.warning(f"Data quality issues: {errors}")
                status = "partial"
            else:
                status = "success"

            # Calculate statistics
            stats = processor.calculate_statistics(rates)
            arbitrage_opps = processor.find_arbitrage_opportunities(rates)
            arbitrage_count = len(arbitrage_opps)

            # Save to database
            logger.info("Saving to database...")
            if db_client.insert_funding_rates(rates):
                logger.info("Successfully saved to database")
            else:
                logger.error("Failed to save to database")
                status = "partial"

            # Export if requested
            if export_csv:
                csv_path = processor.export_to_csv(rates)
                logger.info(f"Exported to CSV: {csv_path}")

            if export_json:
                json_path = processor.export_to_json(rates, include_stats=True)
                logger.info(f"Exported to JSON: {json_path}")

            # Generate and log summary report
            report = processor.generate_summary_report(rates)
            logger.info(f"\n{report}")

            # Log top arbitrage opportunities
            if arbitrage_opps:
                logger.info(f"Found {arbitrage_count} arbitrage opportunities:")
                for opp in arbitrage_opps[:5]:
                    logger.info(
                        f"  {opp['coin']} ({opp['exchange']}): {opp['arbitrage_value']:.2f}%"
                    )

    except Exception as e:
        logger.error(f"Scraping job failed: {e}", exc_info=True)
        error_message = str(e)
        status = "failed"

    finally:
        # Clean up scraper
        if scraper:
            try:
                scraper.close_driver()
            except:
                pass

        # Calculate duration
        duration = time.time() - start_time

        # Log metrics
        log_scraping_metrics(status, coins_scraped, duration, error_message)

        # Save scraping log to database
        try:
            db_client = SupabaseClient()
            scraping_log = ScrapingLog(
                status=status,
                coins_scraped=coins_scraped,
                duration_seconds=duration,
                error_message=error_message,
                timeframe=timeframe,
                arbitrage_opportunities=arbitrage_count
            )
            db_client.insert_scraping_log(scraping_log)
        except Exception as e:
            logger.error(f"Failed to save scraping log: {e}")

        logger.info(f"Scraping job completed in {duration:.2f}s with status: {status}")

    return status == "success"


def run_all_timeframes() -> None:
    """Run scraping for all configured timeframes."""
    logger = get_logger(__name__)
    logger.info("Running scraping for all timeframes")

    for timeframe in settings.available_timeframes:
        if shutdown_flag:
            logger.info("Shutdown requested, stopping scraping")
            break

        logger.info(f"Processing timeframe: {timeframe}")
        run_scraping_job(timeframe)

        # Wait between timeframes
        if timeframe != settings.available_timeframes[-1]:
            time.sleep(10)


def run_scheduler() -> None:
    """Run the scheduler daemon."""
    logger = get_logger(__name__)
    logger.info(f"Starting scheduler (interval: {settings.run_interval_minutes} minutes)")

    # Update status
    update_app_status(status="running")

    # Schedule the job
    schedule.every(settings.run_interval_minutes).minutes.do(run_all_timeframes)

    # Run immediately
    run_all_timeframes()

    # Keep running
    while not shutdown_flag:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

    logger.info("Scheduler stopped")


def cleanup_old_data() -> None:
    """Clean up old data from the database."""
    logger = get_logger(__name__)

    try:
        db_client = SupabaseClient()
        deleted = db_client.cleanup_old_data(settings.cleanup_days)
        logger.info(f"Cleaned up {deleted} old records")
    except Exception as e:
        logger.error(f"Failed to cleanup old data: {e}")


@click.command()
@click.option(
    "--run-once",
    is_flag=True,
    help="Run scraping once and exit"
)
@click.option(
    "--timeframe",
    type=click.Choice(["hourly", "8hours", "day", "week", "year", "all"]),
    default="hourly",
    help="Timeframe to scrape"
)
@click.option(
    "--daemon",
    is_flag=True,
    help="Run in daemon mode with scheduler"
)
@click.option(
    "--export-csv",
    type=click.Path(),
    help="Export results to CSV file"
)
@click.option(
    "--export-json",
    type=click.Path(),
    help="Export results to JSON file"
)
@click.option(
    "--cleanup",
    is_flag=True,
    help="Clean up old data and exit"
)
@click.option(
    "--test-connection",
    is_flag=True,
    help="Test database connection and exit"
)
@click.option(
    "--stats",
    is_flag=True,
    help="Show scraping statistics and exit"
)
@click.option(
    "--arbitrage",
    is_flag=True,
    help="Show current arbitrage opportunities and exit"
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    default=None,
    help="Override log level from settings"
)
def main(
    run_once: bool,
    timeframe: str,
    daemon: bool,
    export_csv: Optional[str],
    export_json: Optional[str],
    cleanup: bool,
    test_connection: bool,
    stats: bool,
    arbitrage: bool,
    log_level: Optional[str]
):
    """
    Hyperliquid Funding Rate Scraper

    Scrapes funding rate data from Hyperliquid and stores it in Supabase.
    """
    # Setup logging
    log_level = log_level or settings.log_level
    setup_logging(
        log_level=log_level,
        log_file=settings.log_file_path,
        max_bytes=settings.log_max_bytes,
        backup_count=settings.log_backup_count
    )

    logger = get_logger(__name__)
    logger.info("=" * 60)
    logger.info("Hyperliquid Funding Rate Scraper v1.0.0")
    logger.info("=" * 60)

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Handle special commands
        if test_connection:
            logger.info("Testing database connection...")
            db_client = SupabaseClient()
            if db_client.test_connection():
                logger.info("✓ Database connection successful")
                sys.exit(0)
            else:
                logger.error("✗ Database connection failed")
                sys.exit(1)

        if cleanup:
            logger.info("Running data cleanup...")
            cleanup_old_data()
            sys.exit(0)

        if stats:
            logger.info("Fetching scraping statistics...")
            db_client = SupabaseClient()
            stats_data = db_client.get_scraping_stats(hours_back=24)

            if stats_data:
                logger.info("SCRAPING STATISTICS (Last 24 Hours)")
                logger.info("-" * 40)
                for key, value in stats_data.items():
                    logger.info(f"{key}: {value}")
            else:
                logger.info("No statistics available")
            sys.exit(0)

        if arbitrage:
            logger.info("Fetching current arbitrage opportunities...")
            db_client = SupabaseClient()
            processor = DataProcessor()

            rates = db_client.get_latest_funding_rates(timeframe="hourly", limit=500)
            opportunities = processor.find_arbitrage_opportunities(rates)

            if opportunities:
                logger.info(f"ARBITRAGE OPPORTUNITIES (>{settings.arbitrage_threshold}%)")
                logger.info("-" * 40)
                for i, opp in enumerate(opportunities[:20], 1):
                    logger.info(
                        f"{i:2d}. {opp['coin']:10s} ({opp['exchange']:7s}): "
                        f"{opp['arbitrage_value']:+7.2f}%"
                    )
            else:
                logger.info("No arbitrage opportunities found")
            sys.exit(0)

        # Handle CSV/JSON export with specific filename
        export_csv_flag = bool(export_csv)
        export_json_flag = bool(export_json)

        # Main execution modes
        if daemon:
            logger.info("Starting in daemon mode...")

            # Start HTTP server in background thread
            http_thread = threading.Thread(target=start_http_server, args=(8080,), daemon=True)
            http_thread.start()

            # Run scheduler in main thread
            run_scheduler()

        elif run_once or timeframe != "hourly":
            if timeframe == "all":
                logger.info("Running for all timeframes...")
                run_all_timeframes()
            else:
                logger.info(f"Running once for timeframe: {timeframe}")
                success = run_scraping_job(
                    timeframe=timeframe,
                    export_csv=export_csv_flag,
                    export_json=export_json_flag
                )

                # Handle file exports
                if export_csv or export_json:
                    processor = DataProcessor()
                    db_client = SupabaseClient()
                    rates = db_client.get_latest_funding_rates(timeframe, limit=500)

                    if export_csv:
                        csv_path = processor.export_to_csv(rates, filename=export_csv)
                        logger.info(f"Data exported to: {csv_path}")

                    if export_json:
                        json_path = processor.export_to_json(rates, filename=export_json)
                        logger.info(f"Data exported to: {json_path}")

                sys.exit(0 if success else 1)

        else:
            # Default: run scheduler
            logger.info("Starting scheduler (use --run-once for single execution)")
            run_scheduler()

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

    finally:
        logger.info("Scraper shutdown complete")


if __name__ == "__main__":
    main()