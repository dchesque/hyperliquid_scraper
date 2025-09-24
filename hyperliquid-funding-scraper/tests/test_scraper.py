"""Tests for the funding rate scraper."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from decimal import Decimal

from src.scrapers import FundingRateScraper
from src.database.models import FundingRate


class TestFundingRateScraper:
    """Test suite for FundingRateScraper."""

    @pytest.fixture
    def scraper(self):
        """Create a scraper instance for testing."""
        with patch('src.scrapers.base_scraper.webdriver.Chrome'):
            scraper = FundingRateScraper(headless=True)
            scraper.driver = Mock()
            scraper.wait = Mock()
            yield scraper
            scraper.close_driver()

    def test_initialization(self, scraper):
        """Test scraper initialization."""
        assert scraper.headless is True
        assert scraper.current_timeframe == "hourly"

    def test_parse_money_value(self, scraper):
        """Test money value parsing."""
        assert scraper._parse_money_value("$1,234,567") == Decimal("1234567")
        assert scraper._parse_money_value("$1.5M") == Decimal("1500000")
        assert scraper._parse_money_value("$2.3B") == Decimal("2300000000")
        assert scraper._parse_money_value("$500K") == Decimal("500000")
        assert scraper._parse_money_value("invalid") is None

    def test_parse_percentage(self, scraper):
        """Test percentage parsing."""
        assert scraper._parse_percentage("0.0015%") == Decimal("0.0015")
        assert scraper._parse_percentage("-0.0025%") == Decimal("-0.0025")
        assert scraper._parse_percentage("(0.0010%)") == Decimal("-0.0010")
        assert scraper._parse_percentage("invalid") is None

    def test_get_sentiment(self, scraper):
        """Test sentiment detection."""
        # Mock positive element
        positive_cell = Mock()
        positive_cell.get_attribute.return_value = "color: green"
        assert scraper._get_sentiment(positive_cell) == "positive"

        # Mock negative element
        negative_cell = Mock()
        negative_cell.get_attribute.return_value = "color: red"
        assert scraper._get_sentiment(negative_cell) == "negative"

        # Mock neutral element
        neutral_cell = Mock()
        neutral_cell.get_attribute.return_value = ""
        scraper.get_element_text = Mock(return_value="0.0000%")
        assert scraper._get_sentiment(neutral_cell) == "neutral"

    @patch('src.scrapers.funding_scraper.time.sleep')
    def test_select_timeframe(self, mock_sleep, scraper):
        """Test timeframe selection."""
        mock_button = Mock()
        scraper.driver.find_element.return_value = mock_button
        scraper.click_element = Mock(return_value=True)

        assert scraper._select_timeframe("hourly") is True
        assert scraper.current_timeframe == "hourly"

        scraper.driver.find_element.side_effect = Exception("Not found")
        assert scraper._select_timeframe("invalid") is False

    def test_extract_coin_name(self, scraper):
        """Test coin name extraction."""
        cells = []

        # Mock cell with valid coin name
        cell1 = Mock()
        scraper.get_element_text = Mock(return_value="BTC")
        cells.append(cell1)

        assert scraper._extract_coin_name(cells) == "BTC"

        # Test with hyphenated coin
        scraper.get_element_text = Mock(return_value="MATIC-USD")
        assert scraper._extract_coin_name(cells) == "MATIC-USD"

        # Test invalid
        scraper.get_element_text = Mock(return_value="invalid123")
        assert scraper._extract_coin_name(cells) is None


class TestFundingRateModel:
    """Test suite for FundingRate model."""

    def test_funding_rate_creation(self):
        """Test FundingRate creation."""
        rate = FundingRate(
            coin="BTC",
            hyperliquid_oi=Decimal("1000000"),
            hyperliquid_funding=Decimal("0.0015"),
            timeframe="hourly"
        )

        assert rate.coin == "BTC"
        assert rate.hyperliquid_oi == Decimal("1000000")
        assert rate.hyperliquid_funding == Decimal("0.0015")
        assert rate.timeframe == "hourly"

    def test_funding_rate_validation(self):
        """Test FundingRate validation."""
        # Valid rate
        rate = FundingRate(coin="BTC", timeframe="hourly")
        assert rate.validate() is True

        # Invalid timeframe
        rate = FundingRate(coin="BTC", timeframe="invalid")
        assert rate.validate() is False

        # Missing coin
        rate = FundingRate(coin="", timeframe="hourly")
        assert rate.validate() is False

        # Invalid sentiment
        rate = FundingRate(
            coin="BTC",
            timeframe="hourly",
            hyperliquid_sentiment="invalid"
        )
        assert rate.validate() is False

    def test_arbitrage_opportunity(self):
        """Test arbitrage opportunity detection."""
        rate = FundingRate(
            coin="BTC",
            timeframe="hourly",
            binance_hl_arb=Decimal("1.5")
        )
        assert rate.has_arbitrage_opportunity(1.0) is True
        assert rate.has_arbitrage_opportunity(2.0) is False

        rate.binance_hl_arb = None
        rate.bybit_hl_arb = Decimal("-1.2")
        assert rate.has_arbitrage_opportunity(1.0) is True

    def test_to_dict(self):
        """Test conversion to dictionary."""
        rate = FundingRate(
            coin="BTC",
            hyperliquid_oi=Decimal("1000000"),
            hyperliquid_funding=Decimal("0.0015"),
            timeframe="hourly",
            scraped_at=datetime(2024, 1, 1, 12, 0, 0)
        )

        data = rate.to_dict()
        assert data["coin"] == "BTC"
        assert data["hyperliquid_oi"] == 1000000.0
        assert data["hyperliquid_funding"] == 0.0015
        assert data["timeframe"] == "hourly"
        assert "2024-01-01" in data["scraped_at"]

    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "coin": "ETH",
            "hyperliquid_oi": 500000.0,
            "hyperliquid_funding": 0.0025,
            "timeframe": "day",
            "scraped_at": "2024-01-01T12:00:00"
        }

        rate = FundingRate.from_dict(data)
        assert rate.coin == "ETH"
        assert rate.hyperliquid_oi == Decimal("500000")
        assert rate.hyperliquid_funding == Decimal("0.0025")
        assert rate.timeframe == "day"
        assert isinstance(rate.scraped_at, datetime)


class TestDataProcessor:
    """Test suite for DataProcessor."""

    @pytest.fixture
    def processor(self):
        """Create a processor instance for testing."""
        from src.utils import DataProcessor
        return DataProcessor()

    @pytest.fixture
    def sample_rates(self):
        """Create sample funding rates for testing."""
        return [
            FundingRate(
                coin="BTC",
                hyperliquid_oi=Decimal("1000000"),
                hyperliquid_funding=Decimal("0.0015"),
                binance_funding=Decimal("0.0010"),
                binance_hl_arb=Decimal("0.0005"),
                timeframe="hourly"
            ),
            FundingRate(
                coin="ETH",
                hyperliquid_oi=Decimal("500000"),
                hyperliquid_funding=Decimal("-0.0025"),
                bybit_funding=Decimal("-0.0015"),
                bybit_hl_arb=Decimal("-0.0010"),
                timeframe="hourly"
            ),
            FundingRate(
                coin="SOL",
                hyperliquid_oi=Decimal("250000"),
                hyperliquid_funding=Decimal("0.0030"),
                binance_funding=Decimal("0.0010"),
                binance_hl_arb=Decimal("0.0020"),
                timeframe="hourly"
            )
        ]

    def test_calculate_statistics(self, processor, sample_rates):
        """Test statistics calculation."""
        stats = processor.calculate_statistics(sample_rates)

        assert stats["total_coins"] == 3
        assert stats["positive_funding_count"] == 2
        assert stats["negative_funding_count"] == 1
        assert "avg_funding" in stats
        assert "median_funding" in stats
        assert stats["arbitrage_count"] == 1  # Only SOL has arb > 1.0

    def test_find_arbitrage_opportunities(self, processor, sample_rates):
        """Test arbitrage opportunity detection."""
        opportunities = processor.find_arbitrage_opportunities(sample_rates, threshold=0.001)

        assert len(opportunities) == 2  # BTC and SOL have arbitrage
        assert opportunities[0]["coin"] == "SOL"  # Largest arbitrage first
        assert opportunities[0]["arbitrage_value"] == 0.002

    def test_validate_data_quality(self, processor, sample_rates):
        """Test data quality validation."""
        # Valid data
        is_valid, errors = processor.validate_data_quality(sample_rates)
        assert is_valid is False  # Less than 50 coins
        assert "Only 3 coins found" in errors[0]

        # Empty data
        is_valid, errors = processor.validate_data_quality([])
        assert is_valid is False
        assert "No rates provided" in errors

    def test_export_to_csv(self, processor, sample_rates, tmp_path):
        """Test CSV export."""
        processor.export_dir = tmp_path
        filepath = processor.export_to_csv(sample_rates, "test.csv")

        assert filepath.endswith("test.csv")
        assert Path(filepath).exists()

        # Read and verify content
        with open(filepath, 'r') as f:
            content = f.read()
            assert "BTC" in content
            assert "ETH" in content
            assert "SOL" in content

    def test_export_to_json(self, processor, sample_rates, tmp_path):
        """Test JSON export."""
        import json

        processor.export_dir = tmp_path
        filepath = processor.export_to_json(sample_rates, "test.json", include_stats=True)

        assert filepath.endswith("test.json")
        assert Path(filepath).exists()

        # Read and verify content
        with open(filepath, 'r') as f:
            data = json.load(f)
            assert data["total_coins"] == 3
            assert len(data["rates"]) == 3
            assert "statistics" in data
            assert "arbitrage_opportunities" in data


class TestSupabaseClient:
    """Test suite for SupabaseClient."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock Supabase client."""
        with patch('src.database.supabase_client.create_client') as mock_create:
            from src.database import SupabaseClient

            mock_supabase = MagicMock()
            mock_create.return_value = mock_supabase

            client = SupabaseClient(
                url="https://test.supabase.co",
                key="test_key"
            )
            client.client = mock_supabase
            return client

    def test_insert_funding_rates(self, mock_client):
        """Test inserting funding rates."""
        rates = [
            FundingRate(coin="BTC", timeframe="hourly"),
            FundingRate(coin="ETH", timeframe="hourly")
        ]

        mock_client.client.table.return_value.upsert.return_value.execute.return_value = Mock()

        result = mock_client.insert_funding_rates(rates)
        assert result is True
        mock_client.client.table.assert_called_with("funding_rates")

    def test_test_connection(self, mock_client):
        """Test database connection testing."""
        mock_client.client.table.return_value.select.return_value.limit.return_value.execute.return_value = Mock()

        result = mock_client.test_connection()
        assert result is True

        # Test failed connection
        mock_client.client.table.side_effect = Exception("Connection failed")
        result = mock_client.test_connection()
        assert result is False


@pytest.fixture(autouse=True)
def reset_environment():
    """Reset environment for each test."""
    import os
    os.environ["SUPABASE_URL"] = "https://test.supabase.co"
    os.environ["SUPABASE_KEY"] = "test_key"
    yield
    # Cleanup after test