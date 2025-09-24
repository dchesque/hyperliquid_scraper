"""Configuration settings for the Hyperliquid Funding Scraper."""

import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, validator
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Supabase Configuration
    supabase_url: str = Field(..., env="SUPABASE_URL")
    supabase_key: str = Field(..., env="SUPABASE_KEY")

    # Scraping Configuration
    scraping_url: str = Field(
        default="https://data.asxn.xyz/dashboard/hl-funding-rate",
        env="SCRAPING_URL"
    )
    headless_mode: bool = Field(default=True, env="HEADLESS_MODE")
    scraping_timeout: int = Field(default=30, env="SCRAPING_TIMEOUT")
    retry_attempts: int = Field(default=3, env="RETRY_ATTEMPTS")
    page_load_wait: int = Field(default=10, env="PAGE_LOAD_WAIT")
    max_workers: int = Field(default=5, env="MAX_WORKERS")

    # Schedule Configuration
    run_interval_minutes: int = Field(default=60, env="RUN_INTERVAL_MINUTES")
    enable_scheduler: bool = Field(default=False, env="ENABLE_SCHEDULER")

    # Logging Configuration
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: str = Field(default="logs/scraper.log", env="LOG_FILE")
    log_max_bytes: int = Field(default=10485760, env="LOG_MAX_BYTES")
    log_backup_count: int = Field(default=5, env="LOG_BACKUP_COUNT")

    # Data Processing
    arbitrage_threshold: float = Field(default=1.0, env="ARBITRAGE_THRESHOLD")
    batch_insert_size: int = Field(default=50, env="BATCH_INSERT_SIZE")
    cleanup_days: int = Field(default=30, env="CLEANUP_DAYS")

    # Chrome Driver
    chrome_driver_path: Optional[str] = Field(default=None, env="CHROME_DRIVER_PATH")
    user_agent: str = Field(
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        env="USER_AGENT"
    )

    # Notifications
    enable_notifications: bool = Field(default=False, env="ENABLE_NOTIFICATIONS")
    notification_webhook: Optional[str] = Field(default=None, env="NOTIFICATION_WEBHOOK")

    # Timeframes
    available_timeframes: list[str] = Field(
        default=["hourly", "8hours", "day", "week", "year"]
    )

    @validator("log_level")
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is valid."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()

    @validator("supabase_url")
    def validate_supabase_url(cls, v: str) -> str:
        """Validate Supabase URL format."""
        if not v.startswith("https://") or ".supabase.co" not in v:
            raise ValueError("Invalid Supabase URL format")
        return v

    @validator("arbitrage_threshold")
    def validate_arbitrage_threshold(cls, v: float) -> float:
        """Validate arbitrage threshold is positive."""
        if v <= 0:
            raise ValueError("Arbitrage threshold must be positive")
        return v

    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @property
    def log_file_path(self) -> Path:
        """Get the full path to the log file."""
        return BASE_DIR / self.log_file

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return os.getenv("ENVIRONMENT", "development").lower() == "production"

    def get_chrome_options(self) -> dict:
        """Get Chrome options for Selenium."""
        options = {
            "headless": self.headless_mode,
            "user_agent": self.user_agent,
            "window_size": "1920,1080",
            "disable_gpu": True,
            "no_sandbox": True,
            "disable_dev_shm_usage": True,
            "disable_blink_features": "AutomationControlled",
            "excludeSwitches": ["enable-automation"],
            "useAutomationExtension": False,
        }
        return options


try:
    settings = Settings()
except Exception as e:
    print(f"Error loading settings: {e}")
    print("Please ensure all required environment variables are set in .env file")
    raise