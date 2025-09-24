# Hyperliquid Funding Rate Scraper

A professional, production-ready web scraper for collecting funding rate data from Hyperliquid and storing it in Supabase. Built with Python, Selenium, and designed for scalability and reliability.

## Features

- **Comprehensive Data Collection**: Scrapes funding rates for 200+ cryptocurrencies
- **Multiple Timeframes**: Supports hourly, 8-hour, daily, weekly, and yearly timeframes
- **Real-time Arbitrage Detection**: Identifies arbitrage opportunities between Hyperliquid, Binance, and Bybit
- **Automated Scheduling**: Built-in scheduler for continuous data collection
- **Data Export**: Export to CSV and JSON formats with statistics
- **Robust Error Handling**: Retry logic, fallback mechanisms, and detailed logging
- **Docker Support**: Containerized deployment with Chrome and ChromeDriver pre-installed
- **Production Ready**: Structured logging, data validation, and monitoring capabilities

## Table of Contents

- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Database Setup](#database-setup)
- [Docker Deployment](#docker-deployment)
- [API Reference](#api-reference)
- [Data Models](#data-models)
- [Development](#development)
- [Troubleshooting](#troubleshooting)

## Installation

### Prerequisites

- Python 3.10+
- Chrome browser
- ChromeDriver (automatically installed via webdriver-manager)
- Supabase account

### Local Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/hyperliquid-funding-scraper.git
cd hyperliquid-funding-scraper
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your Supabase credentials
```

## Configuration

### Environment Variables

Create a `.env` file based on `.env.example`:

```env
# Supabase Configuration (Required)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_anon_key

# Scraping Configuration
SCRAPING_URL=https://data.asxn.xyz/dashboard/hl-funding-rate
HEADLESS_MODE=true
SCRAPING_TIMEOUT=30
RETRY_ATTEMPTS=3
PAGE_LOAD_WAIT=10

# Schedule Configuration
RUN_INTERVAL_MINUTES=60
ENABLE_SCHEDULER=false

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/scraper.log

# Data Processing
ARBITRAGE_THRESHOLD=1.0
BATCH_INSERT_SIZE=50
CLEANUP_DAYS=30
```

### Key Configuration Options

- **HEADLESS_MODE**: Run Chrome in headless mode (no GUI)
- **ARBITRAGE_THRESHOLD**: Minimum percentage difference for arbitrage alerts
- **RUN_INTERVAL_MINUTES**: Frequency of scheduled runs
- **CLEANUP_DAYS**: Days of historical data to keep

## Usage

### Command Line Interface

The scraper provides a comprehensive CLI with multiple options:

```bash
# Run once for hourly timeframe
python -m src.main --run-once

# Run for specific timeframe
python -m src.main --run-once --timeframe day

# Run for all timeframes
python -m src.main --run-once --timeframe all

# Run in daemon mode (scheduler)
python -m src.main --daemon

# Export to CSV
python -m src.main --run-once --export-csv output.csv

# Export to JSON with statistics
python -m src.main --run-once --export-json output.json

# Test database connection
python -m src.main --test-connection

# Show scraping statistics
python -m src.main --stats

# Show current arbitrage opportunities
python -m src.main --arbitrage

# Clean up old data
python -m src.main --cleanup
```

### Programmatic Usage

```python
from src.scrapers import FundingRateScraper
from src.database import SupabaseClient
from src.utils import DataProcessor

# Initialize components
scraper = FundingRateScraper(headless=True)
db_client = SupabaseClient()
processor = DataProcessor()

# Scrape funding rates
rates = scraper.scrape_funding_rates(timeframe="hourly")

# Process and analyze
stats = processor.calculate_statistics(rates)
opportunities = processor.find_arbitrage_opportunities(rates)

# Save to database
db_client.insert_funding_rates(rates)

# Export data
processor.export_to_csv(rates, "funding_rates.csv")

# Clean up
scraper.close_driver()
```

## Database Setup

### Supabase Tables

Create the following tables in your Supabase project:

#### funding_rates table:

```sql
CREATE TABLE funding_rates (
    id BIGSERIAL PRIMARY KEY,
    coin VARCHAR(20) NOT NULL,
    hyperliquid_oi DECIMAL(20, 2),
    hyperliquid_funding DECIMAL(10, 6),
    hyperliquid_sentiment VARCHAR(10),
    binance_funding DECIMAL(10, 6),
    bybit_funding DECIMAL(10, 6),
    binance_hl_arb DECIMAL(10, 6),
    bybit_hl_arb DECIMAL(10, 6),
    timeframe VARCHAR(10) NOT NULL,
    rank_by_oi INTEGER,
    is_favorited BOOLEAN DEFAULT FALSE,
    scraped_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(coin, timeframe, scraped_at)
);

-- Create indexes for performance
CREATE INDEX idx_funding_rates_coin ON funding_rates(coin);
CREATE INDEX idx_funding_rates_timeframe ON funding_rates(timeframe);
CREATE INDEX idx_funding_rates_scraped_at ON funding_rates(scraped_at DESC);
```

#### scraping_logs table:

```sql
CREATE TABLE scraping_logs (
    id BIGSERIAL PRIMARY KEY,
    status VARCHAR(20),
    coins_scraped INTEGER,
    duration_seconds DECIMAL(10, 2),
    error_message TEXT,
    timeframe VARCHAR(10),
    total_coins_found INTEGER,
    arbitrage_opportunities INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_scraping_logs_created_at ON scraping_logs(created_at DESC);
CREATE INDEX idx_scraping_logs_status ON scraping_logs(status);
```

## Docker Deployment

### Using Docker Compose

1. Build and run:
```bash
docker-compose up -d
```

2. View logs:
```bash
docker-compose logs -f scraper
```

3. Stop:
```bash
docker-compose down
```

### Using Docker directly

1. Build image:
```bash
docker build -t hyperliquid-scraper .
```

2. Run container:
```bash
docker run -d \
  --name hyperliquid-scraper \
  --env-file .env \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/exports:/app/exports \
  hyperliquid-scraper
```

## API Reference

### Key Classes

#### FundingRateScraper

Main scraper class for collecting funding rate data.

```python
scraper = FundingRateScraper(headless=True)

# Scrape single timeframe
rates = scraper.scrape_funding_rates(timeframe="hourly")

# Scrape all timeframes
all_rates = scraper.scrape_all_timeframes()
```

#### SupabaseClient

Database client for Supabase operations.

```python
client = SupabaseClient()

# Insert funding rates
client.insert_funding_rates(rates)

# Get latest rates
latest = client.get_latest_funding_rates(timeframe="hourly", limit=100)

# Find arbitrage opportunities
opportunities = client.get_arbitrage_opportunities(min_threshold=1.0)

# Get statistics
stats = client.get_scraping_stats(hours_back=24)
```

#### DataProcessor

Data processing and analysis utilities.

```python
processor = DataProcessor()

# Calculate statistics
stats = processor.calculate_statistics(rates)

# Find arbitrage opportunities
opportunities = processor.find_arbitrage_opportunities(rates, threshold=1.0)

# Export data
processor.export_to_csv(rates, "output.csv")
processor.export_to_json(rates, "output.json")

# Generate report
report = processor.generate_summary_report(rates)
```

## Data Models

### FundingRate

```python
@dataclass
class FundingRate:
    coin: str                    # Token symbol (BTC, ETH, etc.)
    hyperliquid_oi: Decimal      # Open Interest in USD
    hyperliquid_funding: Decimal # Funding rate on Hyperliquid (%)
    hyperliquid_sentiment: str   # positive/negative/neutral
    binance_funding: Decimal     # Funding rate on Binance (%)
    bybit_funding: Decimal       # Funding rate on Bybit (%)
    binance_hl_arb: Decimal      # Binance-HL arbitrage (%)
    bybit_hl_arb: Decimal        # Bybit-HL arbitrage (%)
    timeframe: str               # hourly/8hours/day/week/year
    rank_by_oi: int              # Rank by Open Interest
    is_favorited: bool           # Favorited status
    scraped_at: datetime         # Scraping timestamp
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src tests/

# Run specific test file
pytest tests/test_scraper.py
```

### Code Quality

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/
```

### Pre-commit Hooks

Install pre-commit hooks:
```bash
pre-commit install
```

## Monitoring

### Logging

Logs are stored in `logs/scraper.log` with rotation:
- Structured JSON logging available
- Automatic rotation at 10MB
- Keeps 5 backup files

### Metrics

Monitor these key metrics:
- Scraping success rate
- Number of coins scraped
- Arbitrage opportunities detected
- Scraping duration
- Error frequency

### Health Checks

The Docker container includes a health check that verifies:
- Database connectivity
- Scraper functionality

## Troubleshooting

### Common Issues

1. **Chrome/ChromeDriver Issues**
   ```bash
   # Update ChromeDriver
   pip install --upgrade webdriver-manager
   ```

2. **Database Connection Failed**
   - Verify Supabase URL and key
   - Check network connectivity
   - Ensure tables are created

3. **Low Scraping Success Rate**
   - Increase `PAGE_LOAD_WAIT` and `SCRAPING_TIMEOUT`
   - Check if website structure changed
   - Verify Chrome is running correctly

4. **Memory Issues in Docker**
   - Increase memory limits in docker-compose.yml
   - Enable headless mode
   - Reduce batch size

### Debug Mode

Run with debug logging:
```bash
python -m src.main --run-once --log-level DEBUG
```

## Performance Optimization

- **Batch Processing**: Insert data in configurable batches
- **Connection Pooling**: Reuse database connections
- **Parallel Processing**: Support for concurrent scraping
- **Caching**: Smart caching of static data
- **Resource Management**: Automatic cleanup of old data

## Security Considerations

- Store sensitive credentials in environment variables
- Use read-only database credentials when possible
- Regularly rotate API keys
- Monitor for unusual activity
- Implement rate limiting

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## License

MIT License - see LICENSE file for details

## Support

For issues, questions, or contributions, please open an issue on GitHub.

## Acknowledgments

- Built with Selenium WebDriver
- Powered by Supabase
- Data from Hyperliquid exchange