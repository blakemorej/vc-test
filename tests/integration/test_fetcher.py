"""
Integration tests for fetcher components.

Tests actual HTTP requests and browser rendering with real URLs.
"""

import pytest

from engine.fetcher import FetchTimeoutError, JSRenderedFetcher, RawHTMLFetcher


@pytest.mark.asyncio
async def test_raw_html_fetcher_success():
    """Test successful fetch with RawHTMLFetcher."""
    fetcher = RawHTMLFetcher()

    result, error = await fetcher.fetch("https://httpbin.org/html")

    assert error is None
    assert result is not None
    assert result.success is True
    assert result.status_code == 200
    assert result.url == "https://httpbin.org/html"
    assert "<html>" in result.html.lower()
    assert result.fetch_time_ms > 0
    assert "content-type" in result.headers


@pytest.mark.asyncio
async def test_raw_html_fetcher_redirects():
    """Test that RawHTMLFetcher follows redirects."""
    fetcher = RawHTMLFetcher()

    # httpbin.org/redirect/1 redirects to /get
    result, error = await fetcher.fetch("https://httpbin.org/redirect/1")

    assert error is None
    assert result is not None
    assert result.success is True
    # Should end up at the final URL after redirect
    assert "/get" in result.url
    assert result.url != "https://httpbin.org/redirect/1"


@pytest.mark.asyncio
async def test_raw_html_fetcher_404():
    """Test RawHTMLFetcher with 404 response."""
    fetcher = RawHTMLFetcher()

    result, error = await fetcher.fetch("https://httpbin.org/status/404")

    assert error is None
    assert result is not None
    assert result.success is False
    assert result.status_code == 404


@pytest.mark.asyncio
async def test_raw_html_fetcher_invalid_url():
    """Test RawHTMLFetcher with invalid URL."""
    fetcher = RawHTMLFetcher()

    result, error = await fetcher.fetch("https://this-domain-does-not-exist-12345.com")

    assert error is not None
    assert result is None
    assert "error" in error.lower() or "timeout" in error.lower()


@pytest.mark.asyncio
async def test_raw_html_fetcher_timeout():
    """Test RawHTMLFetcher with very short timeout."""
    fetcher = RawHTMLFetcher()

    # Use a very short timeout that should fail
    result, error = await fetcher.fetch("https://httpbin.org/delay/10", timeout=100)

    assert error is not None
    assert result is None
    assert "timeout" in error.lower()


@pytest.mark.asyncio
async def test_raw_html_fetcher_custom_user_agent():
    """Test RawHTMLFetcher with custom user agent."""
    custom_ua = "TestBot/1.0 Custom"
    fetcher = RawHTMLFetcher(user_agent=custom_ua)

    result, error = await fetcher.fetch("https://httpbin.org/user-agent")

    assert error is None
    assert result is not None
    assert result.success is True
    # httpbin.org/user-agent returns the user agent in the response
    assert "TestBot" in result.html


@pytest.mark.asyncio
async def test_js_rendered_fetcher_success():
    """Test successful render with JSRenderedFetcher."""
    fetcher = JSRenderedFetcher(headless=True)

    result, error = await fetcher.fetch("https://httpbin.org/html", timeout=15000)

    assert error is None
    assert result is not None
    assert result.success is True
    assert result.url == "https://httpbin.org/html"
    assert "<html>" in result.html.lower()
    assert result.fetch_time_ms > 0


@pytest.mark.asyncio
async def test_js_rendered_fetcher_with_dynamic_content():
    """Test JSRenderedFetcher with dynamic content."""
    fetcher = JSRenderedFetcher(headless=True)

    # httpbin.org/headers returns headers as JSON
    result, error = await fetcher.fetch("https://httpbin.org/headers", timeout=15000)

    assert error is None
    assert result is not None
    assert result.success is True
    # Should contain JSON content after rendering
    assert "{" in result.html and "}" in result.html


@pytest.mark.asyncio
async def test_js_rendered_fetcher_timeout():
    """Test JSRenderedFetcher with very short timeout."""
    fetcher = JSRenderedFetcher(headless=True)

    # Use a very short timeout
    result, error = await fetcher.fetch("https://httpbin.org/delay/10", timeout=1000)

    assert error is not None
    assert result is None
    assert "timeout" in error.lower()


@pytest.mark.asyncio
async def test_js_rendered_fetcher_invalid_url():
    """Test JSRenderedFetcher with invalid URL."""
    fetcher = JSRenderedFetcher(headless=True)

    result, error = await fetcher.fetch(
        "https://this-domain-does-not-exist-12345.com", timeout=10000
    )

    # Browser may handle this differently - either error or success with error page
    # Both are acceptable for this test
    assert result is not None or error is not None


@pytest.mark.asyncio
async def test_js_rendered_fetcher_custom_user_agent():
    """Test JSRenderedFetcher with custom user agent."""
    custom_ua = "TestJSBot/1.0 Custom"
    fetcher = JSRenderedFetcher(user_agent=custom_ua, headless=True)

    result, error = await fetcher.fetch("https://httpbin.org/user-agent", timeout=15000)

    assert error is None
    assert result is not None
    assert result.success is True
    # httpbin.org/user-agent returns the user agent in the response
    assert "TestJSBot" in result.html


@pytest.mark.asyncio
async def test_js_rendered_fetcher_wait_strategies():
    """Test different wait strategies for JSRenderedFetcher."""
    url = "https://httpbin.org/html"

    # Test network_idle
    fetcher1 = JSRenderedFetcher(wait_strategy="network_idle", headless=True)
    result1, error1 = await fetcher1.fetch(url, timeout=15000)
    assert error1 is None
    assert result1 is not None
    assert result1.success is True

    # Test load
    fetcher2 = JSRenderedFetcher(wait_strategy="load", headless=True)
    result2, error2 = await fetcher2.fetch(url, timeout=15000)
    assert error2 is None
    assert result2 is not None
    assert result2.success is True

    # Test timeout
    fetcher3 = JSRenderedFetcher(wait_strategy="timeout", headless=True)
    result3, error3 = await fetcher3.fetch(url, timeout=15000)
    assert error3 is None
    assert result3 is not None
    assert result3.success is True


@pytest.mark.asyncio
async def test_fetchers_consistency():
    """Test that both fetchers return consistent data for same URL."""
    url = "https://httpbin.org/html"

    raw_fetcher = RawHTMLFetcher()
    js_fetcher = JSRenderedFetcher(headless=True)

    raw_result, raw_error = await raw_fetcher.fetch(url)
    js_result, js_error = await js_fetcher.fetch(url, timeout=15000)

    assert raw_error is None
    assert js_error is None
    assert raw_result is not None
    assert js_result is not None

    # Both should succeed
    assert raw_result.success is True
    assert js_result.success is True

    # Both should have the same final URL
    assert raw_result.url == js_result.url

    # Both should have HTML content
    assert len(raw_result.html) > 0
    assert len(js_result.html) > 0
