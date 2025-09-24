"""Scrapers module for the Hyperliquid Funding Scraper."""

from .base_scraper import BaseScraper
from .funding_scraper import FundingRateScraper

__all__ = ["BaseScraper", "FundingRateScraper"]