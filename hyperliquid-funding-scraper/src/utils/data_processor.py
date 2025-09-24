"""Data processing utilities with Python 3.13 compatibility."""

import csv
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

from src.database.models import FundingRate, CoinStats, FundingRateSnapshot
from src.config import settings
from src.utils.logger import get_logger, LoggerMixin

# Try to import pandas/numpy, with fallback to polars or pure Python
HAS_PANDAS = False
HAS_POLARS = False

try:
    import pandas as pd
    import numpy as np
    HAS_PANDAS = True
except ImportError:
    try:
        import polars as pl
        HAS_POLARS = True
    except ImportError:
        pass

# Pure Python implementations for statistics if no libraries available
class Statistics:
    """Pure Python statistics functions."""

    @staticmethod
    def mean(values: list) -> float:
        """Calculate mean."""
        return sum(values) / len(values) if values else 0

    @staticmethod
    def median(values: list) -> float:
        """Calculate median."""
        if not values:
            return 0
        sorted_values = sorted(values)
        n = len(sorted_values)
        if n % 2 == 0:
            return (sorted_values[n//2 - 1] + sorted_values[n//2]) / 2
        return sorted_values[n//2]

    @staticmethod
    def std(values: list) -> float:
        """Calculate standard deviation."""
        if not values:
            return 0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5


class DataProcessor(LoggerMixin):
    """Process and analyze funding rate data with compatibility for Python 3.13."""

    def __init__(self):
        """Initialize the data processor."""
        self.export_dir = Path("exports")
        self.export_dir.mkdir(exist_ok=True)

        # Log available libraries
        if HAS_PANDAS:
            self.logger.info("Using pandas/numpy for data processing")
        elif HAS_POLARS:
            self.logger.info("Using polars for data processing")
        else:
            self.logger.info("Using pure Python for data processing")

    def calculate_statistics(self, rates: List[FundingRate]) -> Dict[str, Any]:
        """
        Calculate statistics from funding rates.

        Args:
            rates: List of funding rates

        Returns:
            Dictionary with statistics
        """
        if not rates:
            return {}

        snapshot = FundingRateSnapshot(rates)
        stats = snapshot.get_stats()

        # Add additional statistics
        funding_values = [float(r.hyperliquid_funding) for r in rates if r.hyperliquid_funding]

        if funding_values:
            if HAS_PANDAS:
                stats.update({
                    "avg_funding": np.mean(funding_values),
                    "median_funding": np.median(funding_values),
                    "std_funding": np.std(funding_values),
                    "min_funding": min(funding_values),
                    "max_funding": max(funding_values),
                })
            else:
                # Use pure Python statistics
                stats.update({
                    "avg_funding": Statistics.mean(funding_values),
                    "median_funding": Statistics.median(funding_values),
                    "std_funding": Statistics.std(funding_values),
                    "min_funding": min(funding_values),
                    "max_funding": max(funding_values),
                })

        # Calculate arbitrage statistics
        arb_opportunities = self.find_arbitrage_opportunities(rates)
        stats["arbitrage_count"] = len(arb_opportunities)

        if arb_opportunities:
            arb_values = [float(opp["arbitrage_value"]) for opp in arb_opportunities]
            stats["max_arbitrage"] = max(arb_values)
            stats["avg_arbitrage"] = Statistics.mean(arb_values) if not HAS_PANDAS else np.mean(arb_values)

        self.logger.info(f"Calculated statistics for {len(rates)} rates")
        return stats

    def find_arbitrage_opportunities(
        self,
        rates: List[FundingRate],
        threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Find arbitrage opportunities in funding rates.

        Args:
            rates: List of funding rates
            threshold: Minimum arbitrage threshold

        Returns:
            List of arbitrage opportunities
        """
        threshold = threshold or settings.arbitrage_threshold
        opportunities = []

        for rate in rates:
            # Check Binance arbitrage
            if rate.binance_hl_arb and abs(float(rate.binance_hl_arb)) >= threshold:
                opportunities.append({
                    "coin": rate.coin,
                    "exchange": "Binance",
                    "hyperliquid_funding": float(rate.hyperliquid_funding) if rate.hyperliquid_funding else 0,
                    "exchange_funding": float(rate.binance_funding) if rate.binance_funding else 0,
                    "arbitrage_value": float(rate.binance_hl_arb),
                    "timeframe": rate.timeframe,
                    "timestamp": rate.scraped_at.isoformat()
                })

            # Check Bybit arbitrage
            if rate.bybit_hl_arb and abs(float(rate.bybit_hl_arb)) >= threshold:
                opportunities.append({
                    "coin": rate.coin,
                    "exchange": "Bybit",
                    "hyperliquid_funding": float(rate.hyperliquid_funding) if rate.hyperliquid_funding else 0,
                    "exchange_funding": float(rate.bybit_funding) if rate.bybit_funding else 0,
                    "arbitrage_value": float(rate.bybit_hl_arb),
                    "timeframe": rate.timeframe,
                    "timestamp": rate.scraped_at.isoformat()
                })

        # Sort by arbitrage value
        opportunities.sort(key=lambda x: abs(x["arbitrage_value"]), reverse=True)

        if opportunities:
            self.logger.info(f"Found {len(opportunities)} arbitrage opportunities above {threshold}%")

        return opportunities

    def identify_trends(
        self,
        historical_rates: List[FundingRate],
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        Identify trends in funding rates over time.

        Args:
            historical_rates: List of historical funding rates
            hours: Hours to analyze

        Returns:
            Dictionary with trend analysis
        """
        if not historical_rates:
            return {}

        # Group by coin
        coin_data = {}
        for rate in historical_rates:
            if rate.coin not in coin_data:
                coin_data[rate.coin] = []
            coin_data[rate.coin].append(rate)

        trends = {
            "rising": [],
            "falling": [],
            "volatile": [],
            "stable": []
        }

        for coin, rates in coin_data.items():
            if len(rates) < 2:
                continue

            # Sort by time
            rates.sort(key=lambda x: x.scraped_at)

            # Get funding values
            values = [float(r.hyperliquid_funding) for r in rates if r.hyperliquid_funding]

            if len(values) < 2:
                continue

            # Calculate trend metrics
            first_half_values = values[:len(values)//2]
            second_half_values = values[len(values)//2:]

            first_half = Statistics.mean(first_half_values)
            second_half = Statistics.mean(second_half_values)
            std_dev = Statistics.std(values)
            change_pct = ((second_half - first_half) / abs(first_half)) * 100 if first_half != 0 else 0

            trend_data = {
                "coin": coin,
                "initial_funding": values[0],
                "current_funding": values[-1],
                "change_pct": change_pct,
                "volatility": std_dev,
                "data_points": len(values)
            }

            # Classify trend
            if std_dev > 0.5:  # High volatility threshold
                trends["volatile"].append(trend_data)
            elif change_pct > 20:
                trends["rising"].append(trend_data)
            elif change_pct < -20:
                trends["falling"].append(trend_data)
            else:
                trends["stable"].append(trend_data)

        # Sort each category
        for category in trends:
            if category in ["rising", "falling"]:
                trends[category].sort(key=lambda x: abs(x["change_pct"]), reverse=True)
            elif category == "volatile":
                trends[category].sort(key=lambda x: x["volatility"], reverse=True)

        self.logger.info(f"Analyzed trends for {len(coin_data)} coins")
        return trends

    def export_to_csv(
        self,
        rates: List[FundingRate],
        filename: Optional[str] = None
    ) -> str:
        """
        Export funding rates to CSV file.

        Args:
            rates: List of funding rates
            filename: Output filename

        Returns:
            Path to exported file
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"funding_rates_{timestamp}.csv"

        filepath = self.export_dir / filename

        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                if not rates:
                    self.logger.warning("No rates to export")
                    return str(filepath)

                # Get fieldnames from first rate
                fieldnames = [
                    "coin", "hyperliquid_oi", "hyperliquid_funding",
                    "hyperliquid_sentiment", "binance_funding", "bybit_funding",
                    "binance_hl_arb", "bybit_hl_arb", "timeframe",
                    "rank_by_oi", "is_favorited", "scraped_at"
                ]

                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()

                for rate in rates:
                    row = rate.to_dict()
                    # Convert Decimal to float for CSV
                    for key in row:
                        if isinstance(row[key], Decimal):
                            row[key] = float(row[key])
                    writer.writerow(row)

            self.logger.info(f"Exported {len(rates)} rates to {filepath}")
            return str(filepath)

        except Exception as e:
            self.logger.error(f"Error exporting to CSV: {e}")
            return ""

    def export_to_json(
        self,
        rates: List[FundingRate],
        filename: Optional[str] = None,
        include_stats: bool = True
    ) -> str:
        """
        Export funding rates to JSON file.

        Args:
            rates: List of funding rates
            filename: Output filename
            include_stats: Whether to include statistics

        Returns:
            Path to exported file
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"funding_rates_{timestamp}.json"

        filepath = self.export_dir / filename

        try:
            data = {
                "timestamp": datetime.utcnow().isoformat(),
                "total_coins": len(rates),
                "rates": [rate.to_dict() for rate in rates]
            }

            if include_stats:
                data["statistics"] = self.calculate_statistics(rates)
                data["arbitrage_opportunities"] = self.find_arbitrage_opportunities(rates)

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)

            self.logger.info(f"Exported {len(rates)} rates to {filepath}")
            return str(filepath)

        except Exception as e:
            self.logger.error(f"Error exporting to JSON: {e}")
            return ""

    def create_dataframe(self, rates: List[FundingRate]):
        """
        Create dataframe from funding rates (pandas or polars).

        Args:
            rates: List of funding rates

        Returns:
            DataFrame (pandas or polars) or dict
        """
        if not rates:
            return {} if not HAS_PANDAS and not HAS_POLARS else None

        data = [rate.to_dict() for rate in rates]

        if HAS_PANDAS:
            df = pd.DataFrame(data)
            # Convert decimal columns to float
            decimal_columns = [
                'hyperliquid_oi', 'hyperliquid_funding', 'binance_funding',
                'bybit_funding', 'binance_hl_arb', 'bybit_hl_arb'
            ]
            for col in decimal_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            # Convert datetime columns
            if 'scraped_at' in df.columns:
                df['scraped_at'] = pd.to_datetime(df['scraped_at'])
            return df

        elif HAS_POLARS:
            df = pl.DataFrame(data)
            # Convert decimal columns to float
            decimal_columns = [
                'hyperliquid_oi', 'hyperliquid_funding', 'binance_funding',
                'bybit_funding', 'binance_hl_arb', 'bybit_hl_arb'
            ]
            for col in decimal_columns:
                if col in df.columns:
                    df = df.with_columns(pl.col(col).cast(pl.Float64))
            return df

        else:
            # Return as list of dicts if no dataframe library available
            return data

    def analyze_coin_performance(
        self,
        coin: str,
        historical_rates: List[FundingRate]
    ) -> CoinStats:
        """
        Analyze performance of a specific coin.

        Args:
            coin: Coin symbol
            historical_rates: Historical rates for the coin

        Returns:
            CoinStats object
        """
        coin_rates = [r for r in historical_rates if r.coin == coin]

        if not coin_rates:
            return CoinStats(coin=coin)

        # Sort by time
        coin_rates.sort(key=lambda x: x.scraped_at)

        # Get funding values
        funding_values = [float(r.hyperliquid_funding) for r in coin_rates if r.hyperliquid_funding]

        # Calculate statistics
        stats = CoinStats(coin=coin)

        if funding_values:
            if HAS_PANDAS:
                stats.avg_funding = np.mean(funding_values)
            else:
                stats.avg_funding = Statistics.mean(funding_values)

            stats.max_funding = max(funding_values)
            stats.min_funding = min(funding_values)

        # Get latest OI
        latest_rate = coin_rates[-1]
        if latest_rate.hyperliquid_oi:
            stats.current_oi = float(latest_rate.hyperliquid_oi)

        # Determine sentiment trend
        sentiments = [r.hyperliquid_sentiment for r in coin_rates[-10:] if r.hyperliquid_sentiment]
        if sentiments:
            positive_count = sentiments.count("positive")
            negative_count = sentiments.count("negative")

            if positive_count > negative_count * 1.5:
                stats.sentiment_trend = "bullish"
            elif negative_count > positive_count * 1.5:
                stats.sentiment_trend = "bearish"
            else:
                stats.sentiment_trend = "neutral"

        # Count arbitrage opportunities
        stats.arbitrage_count = sum(
            1 for r in coin_rates
            if r.has_arbitrage_opportunity(settings.arbitrage_threshold)
        )

        return stats

    def generate_summary_report(
        self,
        rates: List[FundingRate],
        historical_rates: Optional[List[FundingRate]] = None
    ) -> str:
        """
        Generate a summary report of funding rates.

        Args:
            rates: Current funding rates
            historical_rates: Historical rates for comparison

        Returns:
            Report string
        """
        report = []
        report.append("=" * 60)
        report.append("FUNDING RATES SUMMARY REPORT")
        report.append("=" * 60)
        report.append(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        report.append("")

        # Basic statistics
        stats = self.calculate_statistics(rates)
        report.append("OVERVIEW")
        report.append("-" * 40)
        report.append(f"Total Coins: {stats.get('total_coins', 0)}")
        report.append(f"Positive Funding: {stats.get('positive_funding_count', 0)}")
        report.append(f"Negative Funding: {stats.get('negative_funding_count', 0)}")
        report.append(f"Total Open Interest: ${stats.get('total_open_interest', 0):,.2f}")
        report.append("")

        # Funding rate statistics
        if "avg_funding" in stats:
            report.append("FUNDING RATE STATISTICS")
            report.append("-" * 40)
            report.append(f"Average: {stats['avg_funding']:.4f}%")
            report.append(f"Median: {stats['median_funding']:.4f}%")
            report.append(f"Min: {stats['min_funding']:.4f}%")
            report.append(f"Max: {stats['max_funding']:.4f}%")
            report.append(f"Std Dev: {stats['std_funding']:.4f}%")
            report.append("")

        # Top movers
        snapshot = FundingRateSnapshot(rates)

        report.append("TOP POSITIVE FUNDING")
        report.append("-" * 40)
        for i, rate in enumerate(snapshot.top_positive_funding[:5], 1):
            funding = float(rate.hyperliquid_funding) if rate.hyperliquid_funding else 0
            report.append(f"{i}. {rate.coin}: {funding:.4f}%")
        report.append("")

        report.append("TOP NEGATIVE FUNDING")
        report.append("-" * 40)
        for i, rate in enumerate(snapshot.top_negative_funding[:5], 1):
            funding = float(rate.hyperliquid_funding) if rate.hyperliquid_funding else 0
            report.append(f"{i}. {rate.coin}: {funding:.4f}%")
        report.append("")

        # Arbitrage opportunities
        arb_opps = self.find_arbitrage_opportunities(rates)
        if arb_opps:
            report.append(f"ARBITRAGE OPPORTUNITIES (>{settings.arbitrage_threshold}%)")
            report.append("-" * 40)
            for i, opp in enumerate(arb_opps[:5], 1):
                report.append(
                    f"{i}. {opp['coin']} ({opp['exchange']}): {opp['arbitrage_value']:.2f}%"
                )
            report.append("")

        # Trends (if historical data available)
        if historical_rates:
            trends = self.identify_trends(historical_rates)

            if trends.get("volatile"):
                report.append("MOST VOLATILE COINS")
                report.append("-" * 40)
                for i, coin in enumerate(trends["volatile"][:5], 1):
                    report.append(
                        f"{i}. {coin['coin']}: σ={coin['volatility']:.4f}"
                    )
                report.append("")

        report.append("=" * 60)

        report_text = "\n".join(report)
        self.logger.info("Generated summary report")

        return report_text

    def validate_data_quality(self, rates: List[FundingRate]) -> Tuple[bool, List[str]]:
        """
        Validate the quality of scraped data.

        Args:
            rates: List of funding rates

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        if not rates:
            errors.append("No rates provided")
            return False, errors

        # Check for minimum number of coins
        if len(rates) < 50:
            errors.append(f"Only {len(rates)} coins found (expected 200+)")

        # Check for missing critical fields
        missing_funding = sum(1 for r in rates if r.hyperliquid_funding is None)
        if missing_funding > len(rates) * 0.5:
            errors.append(f"Missing funding data for {missing_funding}/{len(rates)} coins")

        # Check for duplicate coins
        coins = [r.coin for r in rates]
        unique_coins = set(coins)
        if len(unique_coins) < len(coins):
            errors.append(f"Duplicate coins found: {len(coins) - len(unique_coins)} duplicates")

        # Check data freshness
        now = datetime.utcnow()
        for rate in rates[:10]:  # Check first 10
            if (now - rate.scraped_at).seconds > 300:  # More than 5 minutes old
                errors.append("Data appears to be stale")
                break

        # Validate individual rates
        invalid_rates = []
        for rate in rates:
            if not rate.validate():
                invalid_rates.append(rate.coin)

        if invalid_rates:
            errors.append(f"Invalid rates for coins: {', '.join(invalid_rates[:5])}")

        is_valid = len(errors) == 0

        if not is_valid:
            self.logger.warning(f"Data quality issues: {'; '.join(errors)}")

        return is_valid, errors