"""Funding rate scraper for Hyperliquid data."""

import time
import re
from typing import List, Dict, Optional, Any
from datetime import datetime
from decimal import Decimal
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException

from src.scrapers.base_scraper import BaseScraper
from src.database.models import FundingRate
from src.config import settings
from src.utils.logger import ScrapeLogger


class FundingRateScraper(BaseScraper):
    """Scraper for Hyperliquid funding rate data."""

    def __init__(self, headless: Optional[bool] = None):
        """Initialize the funding rate scraper."""
        super().__init__(headless)
        self.current_timeframe = "hourly"

    def scrape_funding_rates(
        self,
        timeframe: str = "hourly",
        max_retries: int = 3
    ) -> List[FundingRate]:
        """
        Scrape funding rates for a specific timeframe.

        Args:
            timeframe: Timeframe to scrape
            max_retries: Maximum retry attempts

        Returns:
            List of FundingRate objects
        """
        with ScrapeLogger(f"funding_rates_{timeframe}", self.logger) as log:
            for attempt in range(max_retries):
                try:
                    # Navigate to the page
                    if not self.navigate_to(settings.scraping_url):
                        continue

                    # Wait for page to load
                    self.wait_for_page_load()

                    # Select timeframe
                    if not self._select_timeframe(timeframe):
                        self.logger.warning(f"Failed to select timeframe: {timeframe}")

                    # Wait for table to load
                    time.sleep(3)

                    # Scrape the data
                    rates = self._extract_funding_rates(timeframe)

                    log.add_metric("coins_scraped", len(rates))
                    log.add_metric("timeframe", timeframe)

                    self.logger.info(f"Successfully scraped {len(rates)} funding rates for {timeframe}")
                    return rates

                except Exception as e:
                    self.logger.error(f"Attempt {attempt + 1} failed: {e}")
                    if attempt == max_retries - 1:
                        self.take_screenshot(f"error_{timeframe}")
                    time.sleep(5)

            return []

    def _select_timeframe(self, timeframe: str) -> bool:
        """
        Select a specific timeframe in the UI.

        Args:
            timeframe: Timeframe to select

        Returns:
            Success status
        """
        try:
            # Map timeframe to button text
            timeframe_map = {
                "hourly": "1h",
                "8hours": "8h",
                "day": "1d",
                "week": "1w",
                "year": "1y"
            }

            button_text = timeframe_map.get(timeframe, "1h")

            # Find and click the timeframe button
            # Try multiple selectors as the site structure might vary
            selectors = [
                f"//button[contains(text(), '{button_text}')]",
                f"//div[contains(@class, 'timeframe')]//button[contains(text(), '{button_text}')]",
                f"//span[contains(text(), '{button_text}')]/parent::button",
                f"//button[contains(@aria-label, '{button_text}')]"
            ]

            for selector in selectors:
                try:
                    button = self.driver.find_element(By.XPATH, selector)
                    self.click_element(button, use_js=True)
                    self.current_timeframe = timeframe
                    time.sleep(2)  # Wait for data to reload
                    return True
                except NoSuchElementException:
                    continue

            self.logger.warning(f"Could not find timeframe button for {timeframe}")
            return False

        except Exception as e:
            self.logger.error(f"Error selecting timeframe: {e}")
            return False

    def _extract_funding_rates(self, timeframe: str) -> List[FundingRate]:
        """
        Extract funding rates from the page.

        Args:
            timeframe: Current timeframe

        Returns:
            List of FundingRate objects
        """
        rates = []

        try:
            # Wait for table to be present
            table_selectors = [
                "//table",
                "//div[contains(@class, 'table')]",
                "//div[@role='table']",
                "//tbody"
            ]

            table_element = None
            for selector in table_selectors:
                try:
                    table_element = self.wait_for_element(By.XPATH, selector, timeout=10)
                    if table_element:
                        break
                except:
                    continue

            if not table_element:
                self.logger.error("Could not find table element")
                return rates

            # Get all rows
            row_selectors = [
                ".//tr[position() > 1]",  # Skip header row
                ".//div[@role='row'][position() > 1]",
                ".//tbody//tr"
            ]

            rows = []
            for selector in row_selectors:
                try:
                    rows = table_element.find_elements(By.XPATH, selector)
                    if rows:
                        break
                except:
                    continue

            self.logger.info(f"Found {len(rows)} rows to process")

            # Process each row
            for index, row in enumerate(rows, 1):
                try:
                    rate = self._extract_row_data(row, timeframe, index)
                    if rate and rate.validate():
                        rates.append(rate)
                except Exception as e:
                    self.logger.debug(f"Error processing row {index}: {e}")
                    continue

                # Scroll periodically to load more data
                if index % 20 == 0:
                    self.scroll_page("down", 500)
                    time.sleep(0.5)

        except Exception as e:
            self.logger.error(f"Error extracting funding rates: {e}")

        return rates

    def _extract_row_data(self, row, timeframe: str, rank: int) -> Optional[FundingRate]:
        """
        Extract data from a single row.

        Args:
            row: WebElement representing a table row
            timeframe: Current timeframe
            rank: Row rank by OI

        Returns:
            FundingRate object or None
        """
        try:
            # Get all cells in the row
            cells = row.find_elements(By.XPATH, ".//td | .//div[@role='cell']")

            if len(cells) < 7:  # Minimum expected columns
                return None

            # Extract coin name (usually first or second cell)
            coin = self._extract_coin_name(cells)
            if not coin:
                return None

            # Extract data from cells
            # The exact order might vary, so we try to identify by content
            rate = FundingRate(
                coin=coin,
                timeframe=timeframe,
                rank_by_oi=rank,
                scraped_at=datetime.utcnow()
            )

            # Process each cell
            for i, cell in enumerate(cells):
                cell_text = self.get_element_text(cell)

                # Skip empty cells
                if not cell_text or cell_text == "-":
                    continue

                # Try to identify and extract different data types
                if "$" in cell_text:  # Open Interest
                    rate.hyperliquid_oi = self._parse_money_value(cell_text)

                elif "%" in cell_text:  # Funding rates
                    value = self._parse_percentage(cell_text)
                    if value is not None:
                        # Determine which funding rate based on position or context
                        if i < 4:  # Likely Hyperliquid funding
                            rate.hyperliquid_funding = value
                            rate.hyperliquid_sentiment = self._get_sentiment(cell)
                        elif "binance" in cell_text.lower() or i == 4:
                            rate.binance_funding = value
                        elif "bybit" in cell_text.lower() or i == 5:
                            rate.bybit_funding = value
                        elif i == 6:  # Binance arbitrage
                            rate.binance_hl_arb = value
                        elif i == 7:  # Bybit arbitrage
                            rate.bybit_hl_arb = value

                # Check for favorited status
                if self._is_favorited(cell):
                    rate.is_favorited = True

            return rate

        except Exception as e:
            self.logger.debug(f"Error extracting row data: {e}")
            return None

    def _extract_coin_name(self, cells) -> Optional[str]:
        """
        Extract coin name from cells.

        Args:
            cells: List of cell elements

        Returns:
            Coin name or None
        """
        for cell in cells[:3]:  # Check first 3 cells
            text = self.get_element_text(cell)

            # Look for typical coin patterns
            if re.match(r'^[A-Z]{2,10}(-[A-Z]{2,10})?$', text):
                return text

            # Check for coin in child elements
            try:
                coin_elements = cell.find_elements(By.XPATH, ".//span | .//div | .//a")
                for elem in coin_elements:
                    elem_text = self.get_element_text(elem)
                    if re.match(r'^[A-Z]{2,10}(-[A-Z]{2,10})?$', elem_text):
                        return elem_text
            except:
                continue

        return None

    def _parse_money_value(self, text: str) -> Optional[Decimal]:
        """
        Parse money value from text.

        Args:
            text: Text containing money value

        Returns:
            Decimal value or None
        """
        try:
            # Remove $ and commas
            cleaned = text.replace("$", "").replace(",", "").strip()

            # Handle abbreviations (M, B, K)
            multipliers = {"K": 1000, "M": 1000000, "B": 1000000000}

            for suffix, multiplier in multipliers.items():
                if suffix in cleaned.upper():
                    number = float(cleaned.upper().replace(suffix, "").strip())
                    return Decimal(str(number * multiplier))

            return Decimal(cleaned)

        except Exception as e:
            self.logger.debug(f"Error parsing money value '{text}': {e}")
            return None

    def _parse_percentage(self, text: str) -> Optional[Decimal]:
        """
        Parse percentage value from text.

        Args:
            text: Text containing percentage

        Returns:
            Decimal value or None
        """
        try:
            # Remove % and any extra characters
            cleaned = text.replace("%", "").strip()

            # Handle negative values
            if "(" in cleaned and ")" in cleaned:
                cleaned = "-" + cleaned.replace("(", "").replace(")", "")

            return Decimal(cleaned)

        except Exception as e:
            self.logger.debug(f"Error parsing percentage '{text}': {e}")
            return None

    def _get_sentiment(self, cell) -> str:
        """
        Get sentiment based on cell styling or content.

        Args:
            cell: Cell element

        Returns:
            Sentiment (positive, negative, neutral)
        """
        try:
            # Check for color in style attribute
            style = cell.get_attribute("style") or ""
            class_name = cell.get_attribute("class") or ""
            text = self.get_element_text(cell)

            # Check for color indicators
            if "green" in style.lower() or "green" in class_name.lower():
                return "positive"
            elif "red" in style.lower() or "red" in class_name.lower():
                return "negative"

            # Check text value
            if text:
                value = self._parse_percentage(text)
                if value:
                    if value > 0:
                        return "positive"
                    elif value < 0:
                        return "negative"

            return "neutral"

        except Exception:
            return "neutral"

    def _is_favorited(self, cell) -> bool:
        """
        Check if a coin is marked as favorite.

        Args:
            cell: Cell element

        Returns:
            Favorited status
        """
        try:
            # Look for star or heart icons
            icons = cell.find_elements(By.XPATH, ".//svg | .//i | .//span[contains(@class, 'star')] | .//span[contains(@class, 'favorite')]")
            for icon in icons:
                class_name = icon.get_attribute("class") or ""
                if "star" in class_name.lower() or "favorite" in class_name.lower() or "heart" in class_name.lower():
                    # Check if it's filled/active
                    if "filled" in class_name.lower() or "active" in class_name.lower():
                        return True

            return False

        except Exception:
            return False

    def scrape_all_timeframes(self) -> Dict[str, List[FundingRate]]:
        """
        Scrape funding rates for all available timeframes.

        Returns:
            Dictionary with timeframe as key and rates as value
        """
        all_rates = {}

        for timeframe in settings.available_timeframes:
            self.logger.info(f"Scraping timeframe: {timeframe}")

            rates = self.scrape_funding_rates(timeframe)
            all_rates[timeframe] = rates

            # Wait between timeframes
            if timeframe != settings.available_timeframes[-1]:
                time.sleep(5)

        return all_rates

    def get_table_screenshot(self, filename: str = "funding_table") -> str:
        """
        Take a screenshot of just the funding table.

        Args:
            filename: Screenshot filename

        Returns:
            Path to screenshot
        """
        try:
            # Find table element
            table = self.wait_for_element(By.XPATH, "//table | //div[contains(@class, 'table')]")

            if table:
                # Scroll to table
                self.scroll_to_element(table)

                # Take screenshot of element
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filepath = self.screenshot_dir / f"{filename}_{timestamp}.png"
                table.screenshot(str(filepath))

                self.logger.info(f"Table screenshot saved: {filepath}")
                return str(filepath)

            return self.take_screenshot(filename)

        except Exception as e:
            self.logger.error(f"Error taking table screenshot: {e}")
            return self.take_screenshot(filename)