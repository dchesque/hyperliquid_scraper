"""Base scraper class with common functionality."""

import time
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from retry import retry

from src.config import settings
from src.utils.logger import get_logger, LoggerMixin


class BaseScraper(LoggerMixin):
    """Base class for web scrapers with Selenium."""

    def __init__(self, headless: Optional[bool] = None):
        """
        Initialize the base scraper.

        Args:
            headless: Whether to run browser in headless mode
        """
        self.headless = headless if headless is not None else settings.headless_mode
        self.driver: Optional[webdriver.Chrome] = None
        self.wait: Optional[WebDriverWait] = None
        self.screenshot_dir = Path("screenshots")
        self.screenshot_dir.mkdir(exist_ok=True)

    def setup_driver(self) -> None:
        """Setup Chrome driver with optimal settings."""
        try:
            # Chrome options
            chrome_options = Options()

            if self.headless:
                chrome_options.add_argument("--headless=new")

            # Performance and stability options
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--disable-features=VizDisplayCompositor")
            chrome_options.add_argument("--window-size=1920,1080")

            # Anti-detection options
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option("useAutomationExtension", False)

            # Set user agent
            chrome_options.add_argument(f"user-agent={settings.user_agent}")

            # Disable images and CSS for faster loading (optional)
            prefs = {
                "profile.default_content_setting_values": {
                    "images": 2,  # Block images
                    # "stylesheets": 2,  # Block CSS
                },
                "profile.managed_default_content_settings": {
                    "images": 2
                }
            }
            chrome_options.add_experimental_option("prefs", prefs)

            # Setup driver
            if settings.chrome_driver_path:
                service = Service(settings.chrome_driver_path)
            else:
                # Try local chromedriver first, then use webdriver-manager
                import os
                local_chromedriver = os.path.join(os.getcwd(), "chromedriver.exe")
                if os.path.exists(local_chromedriver):
                    self.logger.info(f"Using local ChromeDriver: {local_chromedriver}")
                    service = Service(local_chromedriver)
                else:
                    # Use webdriver-manager with explicit architecture
                    from webdriver_manager.chrome import ChromeDriverManager
                    from webdriver_manager.core.os_manager import OperationSystemManager

                    # Force 64-bit version for Windows
                    os_name = OperationSystemManager().get_os_name()
                    if "win" in os_name.lower():
                        os.environ["WDM_ARCHITECTURE"] = "64"

                    service = Service(ChromeDriverManager().install())

            self.driver = webdriver.Chrome(service=service, options=chrome_options)

            # Setup wait
            self.wait = WebDriverWait(self.driver, settings.scraping_timeout)

            # Execute anti-detection scripts
            self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5]
                    });
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['en-US', 'en']
                    });
                    window.chrome = {
                        runtime: {}
                    };
                    Object.defineProperty(navigator, 'permissions', {
                        get: () => ({
                            query: () => Promise.resolve({ state: 'granted' })
                        })
                    });
                """
            })

            self.logger.info("Chrome driver setup completed")

        except Exception as e:
            self.logger.error(f"Failed to setup Chrome driver: {e}")
            raise

    def close_driver(self) -> None:
        """Close the Chrome driver."""
        if self.driver:
            try:
                self.driver.quit()
                self.logger.debug("Chrome driver closed")
            except Exception as e:
                self.logger.error(f"Error closing Chrome driver: {e}")
            finally:
                self.driver = None
                self.wait = None

    @retry(tries=3, delay=2, backoff=2)
    def navigate_to(self, url: str) -> bool:
        """
        Navigate to a URL with retry logic.

        Args:
            url: Target URL

        Returns:
            Success status
        """
        try:
            if not self.driver:
                self.setup_driver()

            self.logger.info(f"Navigating to {url}")
            self.driver.get(url)

            # Wait for page to start loading
            time.sleep(2)

            return True

        except TimeoutException:
            self.logger.error(f"Timeout navigating to {url}")
            self.take_screenshot("navigation_timeout")
            return False

        except WebDriverException as e:
            self.logger.error(f"WebDriver error navigating to {url}: {e}")
            return False

    def wait_for_element(
        self,
        by: By,
        value: str,
        timeout: Optional[int] = None,
        condition: Any = EC.presence_of_element_located
    ):
        """
        Wait for an element to be present.

        Args:
            by: Selenium By locator
            value: Locator value
            timeout: Custom timeout
            condition: Expected condition

        Returns:
            WebElement or None
        """
        try:
            timeout = timeout or settings.scraping_timeout
            wait = WebDriverWait(self.driver, timeout)
            element = wait.until(condition((by, value)))
            return element

        except TimeoutException:
            self.logger.warning(f"Element not found: {by}={value}")
            return None

    def wait_for_elements(
        self,
        by: By,
        value: str,
        timeout: Optional[int] = None
    ):
        """
        Wait for multiple elements to be present.

        Args:
            by: Selenium By locator
            value: Locator value
            timeout: Custom timeout

        Returns:
            List of WebElements
        """
        try:
            timeout = timeout or settings.scraping_timeout
            wait = WebDriverWait(self.driver, timeout)
            elements = wait.until(EC.presence_of_all_elements_located((by, value)))
            return elements

        except TimeoutException:
            self.logger.warning(f"Elements not found: {by}={value}")
            return []

    def scroll_to_element(self, element) -> None:
        """
        Scroll to an element.

        Args:
            element: WebElement to scroll to
        """
        try:
            self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
            time.sleep(0.5)
        except Exception as e:
            self.logger.error(f"Error scrolling to element: {e}")

    def scroll_page(self, direction: str = "down", amount: int = 1000) -> None:
        """
        Scroll the page.

        Args:
            direction: up or down
            amount: Pixels to scroll
        """
        try:
            if direction == "down":
                self.driver.execute_script(f"window.scrollBy(0, {amount});")
            else:
                self.driver.execute_script(f"window.scrollBy(0, -{amount});")
            time.sleep(0.5)
        except Exception as e:
            self.logger.error(f"Error scrolling page: {e}")

    def wait_for_page_load(self, timeout: Optional[int] = None) -> bool:
        """
        Wait for page to fully load.

        Args:
            timeout: Custom timeout

        Returns:
            Success status
        """
        try:
            timeout = timeout or settings.page_load_wait

            # Wait for document ready state
            WebDriverWait(self.driver, timeout).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )

            # Additional wait for dynamic content
            time.sleep(2)

            return True

        except TimeoutException:
            self.logger.warning("Page load timeout")
            return False

    def take_screenshot(self, name: str = "screenshot") -> str:
        """
        Take a screenshot for debugging.

        Args:
            name: Screenshot name

        Returns:
            Path to screenshot
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{name}_{timestamp}.png"
            filepath = self.screenshot_dir / filename

            self.driver.save_screenshot(str(filepath))
            self.logger.info(f"Screenshot saved: {filepath}")

            return str(filepath)

        except Exception as e:
            self.logger.error(f"Failed to take screenshot: {e}")
            return ""

    def execute_script(self, script: str, *args) -> Any:
        """
        Execute JavaScript in the browser.

        Args:
            script: JavaScript code
            args: Arguments to pass to script

        Returns:
            Script result
        """
        try:
            return self.driver.execute_script(script, *args)
        except Exception as e:
            self.logger.error(f"Error executing script: {e}")
            return None

    def get_page_source(self) -> str:
        """
        Get the current page source.

        Returns:
            Page HTML source
        """
        try:
            return self.driver.page_source
        except Exception as e:
            self.logger.error(f"Error getting page source: {e}")
            return ""

    def click_element(self, element, use_js: bool = False) -> bool:
        """
        Click an element with fallback to JavaScript.

        Args:
            element: WebElement to click
            use_js: Force JavaScript click

        Returns:
            Success status
        """
        try:
            if use_js:
                self.driver.execute_script("arguments[0].click();", element)
            else:
                try:
                    element.click()
                except:
                    # Fallback to JS click
                    self.driver.execute_script("arguments[0].click();", element)

            time.sleep(0.5)
            return True

        except Exception as e:
            self.logger.error(f"Error clicking element: {e}")
            return False

    def get_element_text(self, element) -> str:
        """
        Get text from an element with fallbacks.

        Args:
            element: WebElement

        Returns:
            Element text
        """
        try:
            # Try standard text property
            text = element.text
            if text:
                return text.strip()

            # Try innerText
            text = element.get_attribute("innerText")
            if text:
                return text.strip()

            # Try textContent
            text = element.get_attribute("textContent")
            if text:
                return text.strip()

            # Try value attribute (for inputs)
            text = element.get_attribute("value")
            if text:
                return text.strip()

            return ""

        except Exception as e:
            self.logger.error(f"Error getting element text: {e}")
            return ""

    def __enter__(self):
        """Context manager entry."""
        self.setup_driver()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close_driver()