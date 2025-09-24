"""Database models for the Hyperliquid Funding Scraper."""

from datetime import datetime
from typing import Optional, Literal
from dataclasses import dataclass, field, asdict
from decimal import Decimal


@dataclass
class FundingRate:
    """Model for funding rate data."""

    coin: str
    hyperliquid_oi: Optional[Decimal] = None
    hyperliquid_funding: Optional[Decimal] = None
    hyperliquid_sentiment: Optional[Literal["positive", "negative", "neutral"]] = None
    binance_funding: Optional[Decimal] = None
    bybit_funding: Optional[Decimal] = None
    binance_hl_arb: Optional[Decimal] = None
    bybit_hl_arb: Optional[Decimal] = None
    timeframe: str = "hourly"
    rank_by_oi: Optional[int] = None
    is_favorited: bool = False
    scraped_at: datetime = field(default_factory=datetime.utcnow)
    id: Optional[int] = None
    created_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for database insertion."""
        data = {}
        for key, value in asdict(self).items():
            if key == "id" and value is None:
                continue
            if key == "created_at" and value is None:
                continue
            if isinstance(value, Decimal):
                data[key] = float(value)
            elif isinstance(value, datetime):
                data[key] = value.isoformat()
            else:
                data[key] = value
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "FundingRate":
        """Create instance from dictionary."""
        # Convert string dates to datetime
        if "scraped_at" in data and isinstance(data["scraped_at"], str):
            data["scraped_at"] = datetime.fromisoformat(data["scraped_at"])
        if "created_at" in data and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])

        # Convert floats to Decimal
        decimal_fields = [
            "hyperliquid_oi", "hyperliquid_funding", "binance_funding",
            "bybit_funding", "binance_hl_arb", "bybit_hl_arb"
        ]
        for field_name in decimal_fields:
            if field_name in data and data[field_name] is not None:
                data[field_name] = Decimal(str(data[field_name]))

        return cls(**data)

    def validate(self) -> bool:
        """Validate the funding rate data."""
        if not self.coin:
            return False
        if self.timeframe not in ["hourly", "8hours", "day", "week", "year"]:
            return False
        if self.hyperliquid_sentiment and self.hyperliquid_sentiment not in ["positive", "negative", "neutral"]:
            return False
        return True

    def has_arbitrage_opportunity(self, threshold: float = 1.0) -> bool:
        """Check if there's an arbitrage opportunity above threshold."""
        if self.binance_hl_arb and abs(float(self.binance_hl_arb)) >= threshold:
            return True
        if self.bybit_hl_arb and abs(float(self.bybit_hl_arb)) >= threshold:
            return True
        return False


@dataclass
class ScrapingLog:
    """Model for scraping log data."""

    status: Literal["success", "partial", "failed"]
    coins_scraped: int
    duration_seconds: float
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    id: Optional[int] = None
    timeframe: Optional[str] = None
    total_coins_found: Optional[int] = None
    arbitrage_opportunities: Optional[int] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for database insertion."""
        data = {}
        for key, value in asdict(self).items():
            if key == "id" and value is None:
                continue
            if isinstance(value, datetime):
                data[key] = value.isoformat()
            else:
                data[key] = value
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "ScrapingLog":
        """Create instance from dictionary."""
        if "created_at" in data and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        return cls(**data)


@dataclass
class CoinStats:
    """Statistics for a specific coin."""

    coin: str
    avg_funding: Optional[float] = None
    max_funding: Optional[float] = None
    min_funding: Optional[float] = None
    current_oi: Optional[float] = None
    sentiment_trend: Optional[str] = None
    arbitrage_count: int = 0
    last_updated: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "coin": self.coin,
            "avg_funding": self.avg_funding,
            "max_funding": self.max_funding,
            "min_funding": self.min_funding,
            "current_oi": self.current_oi,
            "sentiment_trend": self.sentiment_trend,
            "arbitrage_count": self.arbitrage_count,
            "last_updated": self.last_updated.isoformat()
        }


class FundingRateSnapshot:
    """Snapshot of funding rates at a specific time."""

    def __init__(self, rates: list[FundingRate]):
        """Initialize with a list of funding rates."""
        self.rates = rates
        self.timestamp = datetime.utcnow()
        self.total_coins = len(rates)

    @property
    def top_positive_funding(self) -> list[FundingRate]:
        """Get coins with highest positive funding rates."""
        return sorted(
            [r for r in self.rates if r.hyperliquid_funding and r.hyperliquid_funding > 0],
            key=lambda x: x.hyperliquid_funding,
            reverse=True
        )[:10]

    @property
    def top_negative_funding(self) -> list[FundingRate]:
        """Get coins with most negative funding rates."""
        return sorted(
            [r for r in self.rates if r.hyperliquid_funding and r.hyperliquid_funding < 0],
            key=lambda x: x.hyperliquid_funding
        )[:10]

    @property
    def top_arbitrage_opportunities(self) -> list[FundingRate]:
        """Get top arbitrage opportunities."""
        arb_opportunities = []
        for rate in self.rates:
            if rate.binance_hl_arb:
                arb_opportunities.append((rate, abs(float(rate.binance_hl_arb))))
            if rate.bybit_hl_arb:
                arb_opportunities.append((rate, abs(float(rate.bybit_hl_arb))))

        return [r for r, _ in sorted(arb_opportunities, key=lambda x: x[1], reverse=True)[:10]]

    @property
    def top_by_open_interest(self) -> list[FundingRate]:
        """Get coins with highest open interest."""
        return sorted(
            [r for r in self.rates if r.hyperliquid_oi],
            key=lambda x: x.hyperliquid_oi,
            reverse=True
        )[:10]

    def get_stats(self) -> dict:
        """Get snapshot statistics."""
        positive_count = sum(1 for r in self.rates if r.hyperliquid_funding and r.hyperliquid_funding > 0)
        negative_count = sum(1 for r in self.rates if r.hyperliquid_funding and r.hyperliquid_funding < 0)
        neutral_count = self.total_coins - positive_count - negative_count

        total_oi = sum(float(r.hyperliquid_oi) for r in self.rates if r.hyperliquid_oi)

        return {
            "timestamp": self.timestamp.isoformat(),
            "total_coins": self.total_coins,
            "positive_funding_count": positive_count,
            "negative_funding_count": negative_count,
            "neutral_funding_count": neutral_count,
            "total_open_interest": total_oi,
            "arbitrage_opportunities": len([r for r in self.rates if r.has_arbitrage_opportunity()])
        }