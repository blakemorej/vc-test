"""
Core data models for the SEO content difference engine.

All models are pure data structures that can be serialized and reused
by both CLI and future API implementations.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict


@dataclass(frozen=True)
class URLInput:
    """
    Wrapper for a URL input with validation.

    Frozen to ensure immutability once created.
    """

    url: str

    def __post_init__(self):
        """Validate URL format."""
        if not self.url or not isinstance(self.url, str):
            raise ValueError(f"URL must be a non-empty string: {self.url}")

        # Basic validation - http/https scheme required
        url_lower = self.url.lower().strip()
        if not url_lower.startswith(("http://", "https://")):
            raise ValueError(f"URL must start with http:// or https://: {self.url}")


@dataclass
class RawFetchResult:
    """
    Results from fetching a URL without JavaScript execution.

    Represents what non-JS crawlers and AI tools see.
    """

    url: str  # Final URL after redirects
    original_url: str  # URL as requested
    status_code: int
    headers: dict[str, str]
    html: str
    fetch_time_ms: int

    @property
    def success(self) -> bool:
        """Check if the fetch was successful (2xx status)."""
        return 200 <= self.status_code < 300


@dataclass
class RenderedFetchResult:
    """
    Results from fetching a URL with JavaScript enabled.

    Represents what users and JS-capable crawlers see.
    """

    url: str  # Final URL after redirects
    original_url: str  # URL as requested
    html: str
    success: bool
    fetch_time_ms: int
    error_message: str | None = None


@dataclass
class ExtractedContent:
    """
    Structured content extracted from HTML.

    Only includes meaningful content - no scripts, styles, or tracking pixels.
    """

    visible_text: str  # Normalized visible text content
    headings: list[str]  # All H1-H6 headings in order
    internal_links: list[dict[str, str]]  # List of {"href": str, "anchor_text": str}

    def __post_init__(self):
        """Normalize data after creation."""
        # Ensure internal links are dictionaries
        if self.internal_links:
            self.internal_links = [
                link
                if isinstance(link, dict)
                else {
                    "href": link.get("href", ""),  # type: ignore[arg-type]
                    "anchor_text": link.get("anchor_text", ""),  # type: ignore[arg-type]
                }
                for link in self.internal_links
            ]

    @property
    def word_count(self) -> int:
        """Count words in visible text."""
        return len(self.visible_text.split())

    @property
    def heading_count(self) -> int:
        """Count total headings."""
        return len(self.headings)

    @property
    def internal_link_count(self) -> int:
        """Count internal links."""
        return len(self.internal_links)


@dataclass
class DifferenceReport:
    """
    Categorized differences between raw and rendered content.

    Reports what's unique to each version of the page.
    """

    text_only_with_js: list[str]  # Text blocks only visible with JS
    text_only_without_js: list[str]  # Text blocks only visible without JS
    headings_missing_without_js: list[str]  # Headings that disappear without JS
    headings_extra_without_js: list[str]  # Headings that only appear without JS
    internal_links_missing_without_js: list[dict[str, str]]  # Links that disappear without JS
    internal_links_extra_without_js: list[dict[str, str]]  # Links that only appear without JS

    # Metrics
    raw_word_count: int
    rendered_word_count: int
    raw_heading_count: int
    rendered_heading_count: int
    raw_internal_link_count: int
    rendered_internal_link_count: int

    @property
    def word_count_delta(self) -> int:
        """Difference in word count (rendered - raw)."""
        return self.rendered_word_count - self.raw_word_count

    @property
    def word_count_percentage_change(self) -> float:
        """Percentage change in word count."""
        if self.raw_word_count == 0:
            return 0.0
        return round((self.word_count_delta / self.raw_word_count) * 100, 2)

    @property
    def content_invisible_without_js_percentage(self) -> float:
        """
        Percentage of rendered content invisible without JS.

        Calculated as: (rendered_words - raw_words) / rendered_words
        """
        if self.rendered_word_count == 0:
            return 0.0
        if self.raw_word_count >= self.rendered_word_count:
            return 0.0
        return round(
            ((self.rendered_word_count - self.raw_word_count) / self.rendered_word_count) * 100,
            2,
        )


@dataclass
class URLAnalysis:
    """
    Complete analysis for a single URL.

    Combines fetch results, extracted content, and difference report.
    """

    url: str  # Original URL as requested
    final_url: str  # Final URL after redirects (from raw fetch)
    http_status: int

    # Fetch results
    raw_fetch: RawFetchResult | None
    rendered_fetch: RenderedFetchResult | None

    # Extracted content
    raw_content: ExtractedContent | None
    rendered_content: ExtractedContent | None

    # Difference analysis
    differences: DifferenceReport | None

    # Errors
    fetch_errors: list[str] = field(default_factory=list)
    render_errors: list[str] = field(default_factory=list)
    extraction_errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """Check if analysis completed successfully."""
        return (
            len(self.fetch_errors) == 0
            and len(self.render_errors) == 0
            and len(self.extraction_errors) == 0
            and self.raw_content is not None
        )

    @property
    def has_differences(self) -> bool:
        """Check if any differences were detected."""
        if not self.differences:
            return False

        return (
            len(self.differences.text_only_with_js) > 0
            or len(self.differences.text_only_without_js) > 0
            or len(self.differences.headings_missing_without_js) > 0
            or len(self.differences.headings_extra_without_js) > 0
            or len(self.differences.internal_links_missing_without_js) > 0
            or len(self.differences.internal_links_extra_without_js) > 0
        )

    def to_dict(self) -> dict:
        """
        Convert analysis to dictionary for serialization.

        Used for JSON/CSV export and API responses.
        """
        diff = self.differences

        return {
            "url": self.url,
            "final_url": self.final_url,
            "http_status": self.http_status,
            "raw_word_count": diff.raw_word_count if diff else 0,
            "rendered_word_count": diff.rendered_word_count if diff else 0,
            "word_count_delta": diff.word_count_delta if diff else 0,
            "content_invisible_without_js_percentage": diff.content_invisible_without_js_percentage
            if diff
            else 0.0,
            "headings_missing_without_js": diff.headings_missing_without_js if diff else [],
            "internal_links_missing_count": len(diff.internal_links_missing_without_js)
            if diff
            else 0,
            "fetch_errors": self.fetch_errors,
            "render_errors": self.render_errors,
            "extraction_errors": self.extraction_errors,
            "success": self.success,
        }


@dataclass
class JobResult:
    """
    Complete results for a batch of URLs.

    Represents the full output of a job run.
    """

    started_at: datetime
    finished_at: Optional[datetime]
    urls_processed: int
    urls_succeeded: int
    urls_failed: int
    results: list[URLAnalysis]

    @property
    def success_rate(self) -> float:
        """Percentage of URLs processed successfully."""
        if self.urls_processed == 0:
            return 0.0
        return round((self.urls_succeeded / self.urls_processed) * 100, 2)

    @property
    def total_errors(self) -> int:
        """Total number of URLs with errors."""
        return self.urls_failed

    def get_failed_analyses(self) -> list[URLAnalysis]:
        """Get all analyses that failed."""
        return [result for result in self.results if not result.success]

    def get_analyses_with_differences(self) -> list[URLAnalysis]:
        """Get all analyses that have detected differences."""
        return [result for result in self.results if result.has_differences]
