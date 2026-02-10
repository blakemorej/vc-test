"""
Unit tests for core data models.
"""

from datetime import datetime

import pytest

from engine.models import (
    DifferenceReport,
    ExtractedContent,
    JobResult,
    RawFetchResult,
    RenderedFetchResult,
    URLAnalysis,
    URLInput,
)


class TestURLInput:
    """Tests for URLInput model."""

    def test_valid_http_url(self):
        """Test that valid HTTP URL is accepted."""
        url_input = URLInput("http://example.com")
        assert url_input.url == "http://example.com"

    def test_valid_https_url(self):
        """Test that valid HTTPS URL is accepted."""
        url_input = URLInput("https://example.com/path")
        assert url_input.url == "https://example.com/path"

    def test_url_trims_whitespace(self):
        """Test that URL input is not automatically trimmed."""
        # URLInput does not trim - validation should catch whitespace issues
        with pytest.raises(ValueError):
            URLInput("  https://example.com  ")

    def test_invalid_url_no_scheme(self):
        """Test that URL without http/https scheme is rejected."""
        with pytest.raises(ValueError, match="must start with http:// or https://"):
            URLInput("example.com")

    def test_invalid_url_empty(self):
        """Test that empty URL is rejected."""
        with pytest.raises(ValueError, match="non-empty string"):
            URLInput("")

    def test_invalid_url_none(self):
        """Test that None URL is rejected."""
        with pytest.raises(ValueError, match="must be a non-empty string"):
            URLInput(None)


class TestRawFetchResult:
    """Tests for RawFetchResult model."""

    def test_success_property_true_for_2xx(self):
        """Test that success is True for 2xx status codes."""
        for status in [200, 201, 204, 299]:
            result = RawFetchResult(
                url="https://example.com",
                original_url="https://example.com",
                status_code=status,
                headers={},
                html="<html></html>",
                fetch_time_ms=100,
            )
            assert result.success is True

    def test_success_property_false_for_non_2xx(self):
        """Test that success is False for non-2xx status codes."""
        for status in [100, 301, 302, 400, 404, 500, 503]:
            result = RawFetchResult(
                url="https://example.com",
                original_url="https://example.com",
                status_code=status,
                headers={},
                html="<html></html>",
                fetch_time_ms=100,
            )
            assert result.success is False


class TestRenderedFetchResult:
    """Tests for RenderedFetchResult model."""

    def test_successful_render(self):
        """Test successful render result."""
        result = RenderedFetchResult(
            url="https://example.com",
            original_url="https://example.com",
            html="<html><body>Rendered content</body></html>",
            success=True,
            fetch_time_ms=500,
        )
        assert result.success is True
        assert result.error_message is None

    def test_failed_render_with_error(self):
        """Test failed render with error message."""
        result = RenderedFetchResult(
            url="https://example.com",
            original_url="https://example.com",
            html="",
            success=False,
            fetch_time_ms=100,
            error_message="Timeout exceeded",
        )
        assert result.success is False
        assert result.error_message == "Timeout exceeded"


class TestExtractedContent:
    """Tests for ExtractedContent model."""

    def test_word_count(self):
        """Test word count calculation."""
        content = ExtractedContent(
            visible_text="Hello world this is a test",
            headings=[],
            internal_links=[],
        )
        assert content.word_count == 6

    def test_word_count_empty(self):
        """Test word count with empty text."""
        content = ExtractedContent(
            visible_text="",
            headings=[],
            internal_links=[],
        )
        assert content.word_count == 0

    def test_heading_count(self):
        """Test heading count."""
        content = ExtractedContent(
            visible_text="",
            headings=["H1", "H2a", "H2b", "H3"],
            internal_links=[],
        )
        assert content.heading_count == 4

    def test_internal_link_count(self):
        """Test internal link count."""
        content = ExtractedContent(
            visible_text="",
            headings=[],
            internal_links=[
                {"href": "/about", "anchor_text": "About"},
                {"href": "/contact", "anchor_text": "Contact"},
                {"href": "/blog", "anchor_text": "Blog"},
            ],
        )
        assert content.internal_link_count == 3

    def test_internal_links_normalization(self):
        """Test that internal links are normalized to dictionaries."""
        content = ExtractedContent(
            visible_text="",
            headings=[],
            internal_links=[
                {"href": "/about", "anchor_text": "About"},
                {"href": "/contact", "anchor_text": "Contact"},
            ],
        )
        assert content.internal_links[0] == {"href": "/about", "anchor_text": "About"}
        assert content.internal_links[1] == {"href": "/contact", "anchor_text": "Contact"}


class TestDifferenceReport:
    """Tests for DifferenceReport model."""

    def test_word_count_delta(self):
        """Test word count delta calculation."""
        diff = DifferenceReport(
            text_only_with_js=[],
            text_only_without_js=[],
            headings_missing_without_js=[],
            headings_extra_without_js=[],
            internal_links_missing_without_js=[],
            internal_links_extra_without_js=[],
            raw_word_count=100,
            rendered_word_count=150,
            raw_heading_count=5,
            rendered_heading_count=7,
            raw_internal_link_count=10,
            rendered_internal_link_count=15,
        )
        assert diff.word_count_delta == 50

    def test_word_count_delta_negative(self):
        """Test word count delta when rendered has fewer words."""
        diff = DifferenceReport(
            text_only_with_js=[],
            text_only_without_js=[],
            headings_missing_without_js=[],
            headings_extra_without_js=[],
            internal_links_missing_without_js=[],
            internal_links_extra_without_js=[],
            raw_word_count=150,
            rendered_word_count=100,
            raw_heading_count=5,
            rendered_heading_count=7,
            raw_internal_link_count=10,
            rendered_internal_link_count=15,
        )
        assert diff.word_count_delta == -50

    def test_word_count_percentage_change(self):
        """Test percentage change calculation."""
        diff = DifferenceReport(
            text_only_with_js=[],
            text_only_without_js=[],
            headings_missing_without_js=[],
            headings_extra_without_js=[],
            internal_links_missing_without_js=[],
            internal_links_extra_without_js=[],
            raw_word_count=100,
            rendered_word_count=150,
            raw_heading_count=5,
            rendered_heading_count=7,
            raw_internal_link_count=10,
            rendered_internal_link_count=15,
        )
        assert diff.word_count_percentage_change == 50.0

    def test_content_invisible_without_js_percentage(self):
        """Test percentage of content invisible without JS."""
        # 100 rendered words, 50 raw words = 50% invisible
        diff = DifferenceReport(
            text_only_with_js=[],
            text_only_without_js=[],
            headings_missing_without_js=[],
            headings_extra_without_js=[],
            internal_links_missing_without_js=[],
            internal_links_extra_without_js=[],
            raw_word_count=50,
            rendered_word_count=100,
            raw_heading_count=5,
            rendered_heading_count=7,
            raw_internal_link_count=10,
            rendered_internal_link_count=15,
        )
        assert diff.content_invisible_without_js_percentage == 50.0

    def test_content_invisible_zero_when_more_without_js(self):
        """Test that percentage is 0 when raw has more words than rendered."""
        diff = DifferenceReport(
            text_only_with_js=[],
            text_only_without_js=[],
            headings_missing_without_js=[],
            headings_extra_without_js=[],
            internal_links_missing_without_js=[],
            internal_links_extra_without_js=[],
            raw_word_count=150,
            rendered_word_count=100,
            raw_heading_count=5,
            rendered_heading_count=7,
            raw_internal_link_count=10,
            rendered_internal_link_count=15,
        )
        assert diff.content_invisible_without_js_percentage == 0.0

    def test_content_invisible_zero_when_equal(self):
        """Test that percentage is 0 when word counts are equal."""
        diff = DifferenceReport(
            text_only_with_js=[],
            text_only_without_js=[],
            headings_missing_without_js=[],
            headings_extra_without_js=[],
            internal_links_missing_without_js=[],
            internal_links_extra_without_js=[],
            raw_word_count=100,
            rendered_word_count=100,
            raw_heading_count=5,
            rendered_heading_count=7,
            raw_internal_link_count=10,
            rendered_internal_link_count=15,
        )
        assert diff.content_invisible_without_js_percentage == 0.0


class TestURLAnalysis:
    """Tests for URLAnalysis model."""

    def test_success_true_no_errors(self):
        """Test that success is True when no errors and content exists."""
        raw_content = ExtractedContent(
            visible_text="Test content",
            headings=["H1"],
            internal_links=[],
        )
        diff = DifferenceReport(
            text_only_with_js=[],
            text_only_without_js=[],
            headings_missing_without_js=[],
            headings_extra_without_js=[],
            internal_links_missing_without_js=[],
            internal_links_extra_without_js=[],
            raw_word_count=2,
            rendered_word_count=2,
            raw_heading_count=1,
            rendered_heading_count=1,
            raw_internal_link_count=0,
            rendered_internal_link_count=0,
        )

        analysis = URLAnalysis(
            url="https://example.com",
            final_url="https://example.com",
            http_status=200,
            raw_fetch=None,
            rendered_fetch=None,
            raw_content=raw_content,
            rendered_content=None,
            differences=diff,
            fetch_errors=[],
            render_errors=[],
            extraction_errors=[],
        )
        assert analysis.success is True

    def test_success_false_with_errors(self):
        """Test that success is False when there are errors."""
        raw_content = ExtractedContent(
            visible_text="Test content",
            headings=[],
            internal_links=[],
        )

        analysis = URLAnalysis(
            url="https://example.com",
            final_url="https://example.com",
            http_status=200,
            raw_fetch=None,
            rendered_fetch=None,
            raw_content=raw_content,
            rendered_content=None,
            differences=None,
            fetch_errors=["Timeout exceeded"],
            render_errors=[],
            extraction_errors=[],
        )
        assert analysis.success is False

    def test_has_differences_true(self):
        """Test that has_differences is True when differences exist."""
        diff = DifferenceReport(
            text_only_with_js=["JS only content"],
            text_only_without_js=[],
            headings_missing_without_js=[],
            headings_extra_without_js=[],
            internal_links_missing_without_js=[],
            internal_links_extra_without_js=[],
            raw_word_count=2,
            rendered_word_count=4,
            raw_heading_count=0,
            rendered_heading_count=0,
            raw_internal_link_count=0,
            rendered_internal_link_count=0,
        )

        analysis = URLAnalysis(
            url="https://example.com",
            final_url="https://example.com",
            http_status=200,
            raw_fetch=None,
            rendered_fetch=None,
            raw_content=None,
            rendered_content=None,
            differences=diff,
        )
        assert analysis.has_differences is True

    def test_has_differences_false(self):
        """Test that has_differences is False when no differences."""
        diff = DifferenceReport(
            text_only_with_js=[],
            text_only_without_js=[],
            headings_missing_without_js=[],
            headings_extra_without_js=[],
            internal_links_missing_without_js=[],
            internal_links_extra_without_js=[],
            raw_word_count=2,
            rendered_word_count=2,
            raw_heading_count=0,
            rendered_heading_count=0,
            raw_internal_link_count=0,
            rendered_internal_link_count=0,
        )

        analysis = URLAnalysis(
            url="https://example.com",
            final_url="https://example.com",
            http_status=200,
            raw_fetch=None,
            rendered_fetch=None,
            raw_content=None,
            rendered_content=None,
            differences=diff,
        )
        assert analysis.has_differences is False

    def test_to_dict(self):
        """Test conversion to dictionary."""
        diff = DifferenceReport(
            text_only_with_js=[],
            text_only_without_js=[],
            headings_missing_without_js=["H1"],
            headings_extra_without_js=[],
            internal_links_missing_without_js=[{"href": "/about", "anchor_text": "About"}],
            internal_links_extra_without_js=[],
            raw_word_count=10,
            rendered_word_count=15,
            raw_heading_count=1,
            rendered_heading_count=2,
            raw_internal_link_count=1,
            rendered_internal_link_count=2,
        )

        analysis = URLAnalysis(
            url="https://example.com",
            final_url="https://example.com/redirected",
            http_status=200,
            raw_fetch=None,
            rendered_fetch=None,
            raw_content=None,
            rendered_content=None,
            differences=diff,
        )

        result_dict = analysis.to_dict()

        assert result_dict["url"] == "https://example.com"
        assert result_dict["final_url"] == "https://example.com/redirected"
        assert result_dict["http_status"] == 200
        assert result_dict["raw_word_count"] == 10
        assert result_dict["rendered_word_count"] == 15
        assert result_dict["word_count_delta"] == 5
        assert result_dict["headings_missing_without_js"] == ["H1"]
        assert result_dict["internal_links_missing_count"] == 1
        assert result_dict["success"] is True


class TestJobResult:
    """Tests for JobResult model."""

    def test_success_rate(self):
        """Test success rate calculation."""
        result = JobResult(
            started_at=datetime.now(),
            finished_at=datetime.now(),
            urls_processed=10,
            urls_succeeded=8,
            urls_failed=2,
            results=[],
        )
        assert result.success_rate == 80.0

    def test_success_rate_zero_urls(self):
        """Test success rate with zero URLs."""
        result = JobResult(
            started_at=datetime.now(),
            finished_at=datetime.now(),
            urls_processed=0,
            urls_succeeded=0,
            urls_failed=0,
            results=[],
        )
        assert result.success_rate == 0.0

    def test_total_errors(self):
        """Test total errors count."""
        result = JobResult(
            started_at=datetime.now(),
            finished_at=datetime.now(),
            urls_processed=10,
            urls_succeeded=7,
            urls_failed=3,
            results=[],
        )
        assert result.total_errors == 3

    def test_get_failed_analyses(self):
        """Test filtering for failed analyses."""
        success_analysis = URLAnalysis(
            url="https://example.com/success",
            final_url="https://example.com/success",
            http_status=200,
            raw_fetch=None,
            rendered_fetch=None,
            raw_content=ExtractedContent("test", [], []),
            rendered_content=None,
            differences=None,
        )

        failed_analysis = URLAnalysis(
            url="https://example.com/fail",
            final_url="https://example.com/fail",
            http_status=404,
            raw_fetch=None,
            rendered_fetch=None,
            raw_content=None,
            rendered_content=None,
            differences=None,
            fetch_errors=["Not found"],
        )

        result = JobResult(
            started_at=datetime.now(),
            finished_at=datetime.now(),
            urls_processed=2,
            urls_succeeded=1,
            urls_failed=1,
            results=[success_analysis, failed_analysis],
        )

        failed = result.get_failed_analyses()
        assert len(failed) == 1
        assert failed[0].url == "https://example.com/fail"

    def test_get_analyses_with_differences(self):
        """Test filtering for analyses with differences."""
        no_diff = DifferenceReport(
            text_only_with_js=[],
            text_only_without_js=[],
            headings_missing_without_js=[],
            headings_extra_without_js=[],
            internal_links_missing_without_js=[],
            internal_links_extra_without_js=[],
            raw_word_count=10,
            rendered_word_count=10,
            raw_heading_count=2,
            rendered_heading_count=2,
            raw_internal_link_count=5,
            rendered_internal_link_count=5,
        )

        has_diff = DifferenceReport(
            text_only_with_js=["JS content"],
            text_only_without_js=[],
            headings_missing_without_js=[],
            headings_extra_without_js=[],
            internal_links_missing_without_js=[],
            internal_links_extra_without_js=[],
            raw_word_count=10,
            rendered_word_count=20,
            raw_heading_count=2,
            rendered_heading_count=2,
            raw_internal_link_count=5,
            rendered_internal_link_count=5,
        )

        analysis1 = URLAnalysis(
            url="https://example.com/no-diff",
            final_url="https://example.com/no-diff",
            http_status=200,
            raw_fetch=None,
            rendered_fetch=None,
            raw_content=None,
            rendered_content=None,
            differences=no_diff,
        )

        analysis2 = URLAnalysis(
            url="https://example.com/has-diff",
            final_url="https://example.com/has-diff",
            http_status=200,
            raw_fetch=None,
            rendered_fetch=None,
            raw_content=None,
            rendered_content=None,
            differences=has_diff,
        )

        result = JobResult(
            started_at=datetime.now(),
            finished_at=datetime.now(),
            urls_processed=2,
            urls_succeeded=2,
            urls_failed=0,
            results=[analysis1, analysis2],
        )

        with_diff = result.get_analyses_with_differences()
        assert len(with_diff) == 1
        assert with_diff[0].url == "https://example.com/has-diff"
