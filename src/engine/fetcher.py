"""
Fetcher implementations for retrieving web pages.

Provides both raw HTML fetching (non-JS) and rendered HTML fetching (JS-enabled).
"""

import asyncio
from abc import ABC, abstractmethod

import httpx
from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from .models import RawFetchResult, RenderedFetchResult


class FetchError(Exception):
    """Base exception for fetch errors."""

    pass


class FetchTimeoutError(FetchError):
    """Exception raised when fetch times out."""

    pass


class RenderTimeoutError(FetchError):
    """Exception raised when render times out."""

    pass


class Fetcher(ABC):
    """
    Abstract base class for fetchers.

    Defines the interface for fetching URLs with or without JavaScript execution.
    """

    @abstractmethod
    async def fetch(self, url: str, timeout: int = 30000) -> tuple:
        """
        Fetch a URL.

        Args:
            url: The URL to fetch
            timeout: Timeout in milliseconds

        Returns:
            Tuple containing the fetch result (either RawFetchResult or RenderedFetchResult)
            and optional error message
        """
        pass


class RawHTMLFetcher(Fetcher):
    """
    Fetches URLs without JavaScript execution.

    Uses httpx for HTTP requests. Follows redirects and captures response metadata.
    Represents what non-JS crawlers and AI tools see.
    """

    def __init__(self, user_agent: str | None = None, follow_redirects: bool = True):
        """
        Initialize the raw HTML fetcher.

        Args:
            user_agent: Custom User-Agent header (optional)
            follow_redirects: Whether to follow HTTP redirects
        """
        self.user_agent = user_agent or (
            "Mozilla/5.0 (compatible; SEO-Content-Diff/1.0; +https://example.com/bot)"
        )
        self.follow_redirects = follow_redirects

    async def fetch(
        self, url: str, timeout: int = 30000
    ) -> tuple[RawFetchResult | None, str | None]:
        """
        Fetch URL without JavaScript execution.

        Args:
            url: The URL to fetch
            timeout: Timeout in milliseconds

        Returns:
            Tuple of (RawFetchResult, None) on success, or (None, error_message) on failure
        """
        start_time = asyncio.get_event_loop().time()

        try:
            # Convert timeout to seconds for httpx
            timeout_seconds = timeout / 1000.0

            async with httpx.AsyncClient(
                follow_redirects=self.follow_redirects,
                timeout=timeout_seconds,
                headers={"User-Agent": self.user_agent},
            ) as client:
                response = await client.get(url)

                # Calculate fetch time in milliseconds
                fetch_time_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)

                # Capture response headers
                headers = dict(response.headers)

                result = RawFetchResult(
                    url=str(response.url),  # Final URL after redirects
                    original_url=url,
                    status_code=response.status_code,
                    headers=headers,
                    html=response.text,
                    fetch_time_ms=fetch_time_ms,
                )

                return result, None

        except httpx.TimeoutException:
            return None, f"Timeout after {timeout}ms"
        except httpx.HTTPError as e:
            return None, f"HTTP error: {str(e)}"
        except Exception as e:
            return None, f"Unexpected error: {str(e)}"


class JSRenderedFetcher(Fetcher):
    """
    Fetches URLs with JavaScript execution enabled.

    Uses Playwright for headless browser rendering. Supports configurable wait strategies.
    Represents what users and JS-capable crawlers see.
    """

    def __init__(
        self,
        user_agent: str | None = None,
        wait_strategy: str = "network_idle",
        headless: bool = True,
    ):
        """
        Initialize the JS-enabled fetcher.

        Args:
            user_agent: Custom User-Agent header (optional)
            wait_strategy: Wait strategy ('network_idle', 'load', or 'timeout')
            headless: Whether to run browser in headless mode
        """
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        self.wait_strategy = wait_strategy
        self.headless = headless

    async def fetch(
        self, url: str, timeout: int = 30000
    ) -> tuple[RenderedFetchResult | None, str | None]:
        """
        Fetch URL with JavaScript execution.

        Args:
            url: The URL to fetch
            timeout: Timeout in milliseconds

        Returns:
            Tuple of (RenderedFetchResult, None) on success, or (None, error_message) on failure
        """
        from playwright.async_api import async_playwright

        start_time = asyncio.get_event_loop().time()

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=self.headless)
                page = await browser.new_page()

                # Set user agent
                await page.set_extra_http_headers({"User-Agent": self.user_agent})

                try:
                    # Navigate to URL
                    response = await page.goto(url, wait_until="domcontentloaded", timeout=timeout)

                    if not response:
                        await browser.close()
                        return None, "No response received"

                    # Apply wait strategy
                    await self._wait_for_content(page, timeout)

                    # Get final URL after redirects
                    final_url = page.url

                    # Get rendered HTML
                    html = await page.content()

                    # Calculate fetch time in milliseconds
                    fetch_time_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)

                    result = RenderedFetchResult(
                        url=final_url,
                        original_url=url,
                        html=html,
                        success=True,
                        fetch_time_ms=fetch_time_ms,
                    )

                    await browser.close()
                    return result, None

                except PlaywrightTimeoutError:
                    await browser.close()
                    return None, f"Render timeout after {timeout}ms"
                except Exception as e:
                    await browser.close()
                    return None, f"Render error: {str(e)}"

        except Exception as e:
            return None, f"Browser initialization error: {str(e)}"

    async def _wait_for_content(self, page: Page, timeout: int):
        """
        Apply wait strategy to ensure content is loaded.

        Args:
            page: Playwright Page object
            timeout: Timeout in milliseconds
        """
        if self.wait_strategy == "network_idle":
            # Wait until network is mostly idle (no more than 2 connections for 500ms)
            try:
                await page.wait_for_load_state("networkidle", timeout=timeout)
            except PlaywrightTimeoutError:
                # Fallback to domcontentloaded if networkidle times out
                pass

        elif self.wait_strategy == "load":
            # Wait until load event fires
            await page.wait_for_load_state("load", timeout=timeout)

        elif self.wait_strategy == "timeout":
            # Simple timeout-based wait (wait half of total timeout)
            await asyncio.sleep(timeout / 2000.0)  # Convert to seconds, divide by 2

        else:
            # Default to network idle
            await self._wait_for_content(page, timeout)
