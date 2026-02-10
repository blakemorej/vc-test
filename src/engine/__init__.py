"""
SEO Content Difference Engine.

Core engine for comparing content between JavaScript-enabled and JavaScript-disabled
versions of web pages. Designed to be reusable by CLI and future API implementations.
"""

# Core models
# Main orchestrator
from .job_runner import JobRunner
from .models import (
    DifferenceReport,
    ExtractedContent,
    JobResult,
    RawFetchResult,
    RenderedFetchResult,
    URLAnalysis,
    URLInput,
)

__all__ = [
    # Models
    "URLInput",
    "URLAnalysis",
    "DifferenceReport",
    "ExtractedContent",
    "JobResult",
    "RawFetchResult",
    "RenderedFetchResult",
    # Main entry point
    "JobRunner",
]
