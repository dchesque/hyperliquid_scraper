"""Database module for the Hyperliquid Funding Scraper."""

from .supabase_client import SupabaseClient

from .models import FundingRate, ScrapingLog

__all__ = ["SupabaseClient", "FundingRate", "ScrapingLog"]