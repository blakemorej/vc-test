"""
Job runner for orchestrating the full content comparison pipeline.

Manages fetching, extraction, and comparison for multiple URLs.
"""

import asyncio
from datetime import datetime
from typing import List

from .differ import ContentDiffer
from .extractor import ContentExtractor
from .fetcher import JSRenderedFetcher, RawHTMLFetcher
from .models import JobResult, URLAnalysis, URLInput


class JobRunner:
    """
    Orchestrates the full pipeline for comparing content across multiple URLs.

    Designed to be reusable by both CLI and future API implementations.
    """

    def __init__(
        self,
        max_concurrency: int = 3,
        fetch_timeout: int = 30000,
        render_timeout: int = 30000,
        user_agent: str | None = None,
        wait_strategy: str = "network_idle",
    ):
        """
        Initialize the job runner.

        Args:
            max_concurrency: Maximum number of URLs to process concurrently
            fetch_timeout: Timeout for HTTP fetches in milliseconds
            render_timeout: Timeout for JS rendering in milliseconds
            user_agent: Custom User-Agent header (optional)
            wait_strategy: Wait strategy for JS rendering ('network_idle', 'load', 'timeout')
        """
        self.max_concurrency = max_concurrency
        self.fetch_timeout = fetch_timeout
        self.render_timeout = render_timeout
        self.user_agent = user_agent
        self.wait_strategy = wait_strategy

        # Initialize components
        self.raw_fetcher = RawHTMLFetcher(user_agent=user_agent)
        self.js_fetcher = JSRenderedFetcher(user_agent=user_agent, wait_strategy=wait_strategy)
        self.extractor = ContentExtractor()
        self.differ = ContentDiffer()

    async def run_job_async(self, urls: List[str]) -> JobResult:
        """
        Run a job asynchronously.

        Args:
            urls: List of URLs to process

        Returns:
            JobResult containing all analyses
        """
        started_at = datetime.now()

        # Validate and deduplicate URLs
        validated_urls = self._validate_and_deduplicate(urls)

        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.max_concurrency)

        # Process URLs concurrently
        tasks = [self._process_url(url, semaphore) for url in validated_urls]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results, handling any exceptions
        analyses: List[URLAnalysis] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Create failed analysis
                analyses.append(
                    URLAnalysis(
                        url=validated_urls[i],
                        final_url=validated_urls[i],
                        http_status=0,
                        raw_fetch=None,
                        rendered_fetch=None,
                        raw_content=None,
                        rendered_content=None,
                        differences=None,
                        fetch_errors=[f"Unexpected error: {str(result)}"],
                        render_errors=[],
                        extraction_errors=[],
                    )
                )
            else:
                analyses.append(result)

        finished_at = datetime.now()

        # Calculate statistics
        urls_succeeded = sum(1 for analysis in analyses if analysis.success)
        urls_failed = len(analyses) - urls_succeeded

        return JobResult(
            started_at=started_at,
            finished_at=finished_at,
            urls_processed=len(validated_urls),
            urls_succeeded=urls_succeeded,
            urls_failed=urls_failed,
            results=analyses,
        )

    def run_job(self, urls: List[str]) -> JobResult:
        """
        Run a job synchronously.

        Convenience method that wraps run_job_async.

        Args:
            urls: List of URLs to process

        Returns:
            JobResult containing all analyses
        """
        return asyncio.run(self.run_job_async(urls))

    def _validate_and_deduplicate(self, urls: List[str]) -> List[str]:
        """
        Validate and deduplicate URLs.

        Args:
            urls: List of URLs to validate

        Returns:
            List of validated, deduplicated URLs
        """
        validated = set()

        for url in urls:
            url = url.strip()
            if not url:
                continue

            try:
                URLInput(url)
                validated.add(url)
            except ValueError:
                # Skip invalid URLs
                pass

        return list(validated)

    async def _process_url(
        self,
        url: str,
        semaphore: asyncio.Semaphore,
    ) -> URLAnalysis:
        """
        Process a single URL through the full pipeline.

        Args:
            url: URL to process
            semaphore: Semaphore for concurrency control

        Returns:
            URLAnalysis containing results
        """
        async with semaphore:
            fetch_errors: List[str] = []
            render_errors: List[str] = []
            extraction_errors: List[str] = []

            # Fetch without JS
            raw_fetch, raw_error = await self.raw_fetcher.fetch(url, timeout=self.fetch_timeout)
            if raw_error or raw_fetch is None:
                if raw_error:
                    fetch_errors.append(raw_error)
                # Even if raw fetch fails, we try to get a status code
                http_status = 0
                final_url = url
            else:
                http_status = raw_fetch.status_code
                final_url = raw_fetch.url

            # Fetch with JS (only if raw fetch succeeded)
            rendered_fetch = None
            if raw_fetch:
                rendered_fetch, render_error = await self.js_fetcher.fetch(
                    url, timeout=self.render_timeout
                )
                if render_error:
                    render_errors.append(render_error)

            # Extract content from raw HTML
            raw_content = None
            if raw_fetch:
                try:
                    extractor = ContentExtractor(base_url=raw_fetch.url)
                    raw_content = extractor.extract(raw_fetch.html)
                except Exception as e:
                    extraction_errors.append(f"Raw content extraction failed: {str(e)}")

            # Extract content from rendered HTML
            rendered_content = None
            if rendered_fetch and rendered_fetch.success:
                try:
                    extractor = ContentExtractor(base_url=rendered_fetch.url)
                    rendered_content = extractor.extract(rendered_fetch.html)
                except Exception as e:
                    extraction_errors.append(f"Rendered content extraction failed: {str(e)}")

            # Compare content
            differences = None
            if raw_content and rendered_content:
                try:
                    differ = ContentDiffer()
                    differences = differ.compare(raw_content, rendered_content)
                except Exception as e:
                    extraction_errors.append(f"Content comparison failed: {str(e)}")

            return URLAnalysis(
                url=url,
                final_url=final_url,
                http_status=http_status,
                raw_fetch=raw_fetch,
                rendered_fetch=rendered_fetch,
                raw_content=raw_content,
                rendered_content=rendered_content,
                differences=differences,
                fetch_errors=fetch_errors,
                render_errors=render_errors,
                extraction_errors=extraction_errors,
            )
