"""
Terminal output formatter for CLI.

Handles all display logic - no business logic, just presentation.
"""

from typing import List

from engine.models import JobResult, URLAnalysis


def print_results_summary(result: JobResult) -> None:
    """
    Print a human-readable summary of results to terminal.

    Shows overall statistics and detailed information for URLs with differences.

    Args:
        result: JobResult containing all analyses
    """
    # Print overall summary
    print("\n" + "=" * 80)
    print("SEO CONTENT DIFFERENCE REPORT")
    print("=" * 80)
    print(f"\nURLs Processed: {result.urls_processed}")
    print(f"URLs Succeeded: {result.urls_succeeded}")
    print(f"URLs Failed:    {result.urls_failed}")
    print(f"Success Rate:   {result.success_rate}%")

    if result.finished_at:
        duration = (result.finished_at - result.started_at).total_seconds()
        print(f"Duration:       {duration:.1f} seconds")

    # Get analyses with differences
    analyses_with_differences = result.get_analyses_with_differences()

    print(f"\n{'=' * 80}")
    print(
        f"Differences Detected: {len(analyses_with_differences)} / {result.urls_processed} URLs"
    )
    print(f"{'=' * 80}\n")

    if not analyses_with_differences:
        print("✓ No content differences detected.")
        print("  All URLs have identical content with and without JavaScript.\n")
        return

    # Show details for each URL with differences
    for i, analysis in enumerate(analyses_with_differences, 1):
        print(f"[{i}] {analysis.url}")
        print(f"    Final URL: {analysis.final_url}")
        print(f"    HTTP Status: {analysis.http_status}")

        if analysis.differences:
            diff = analysis.differences

            # Show word count metrics
            print(f"\n    Word Count:")
            print(f"      Without JS: {diff.raw_word_count}")
            print(f"      With JS:    {diff.rendered_word_count}")
            print(
                f"      Delta:      {diff.word_count_delta:+d} ({diff.word_count_percentage_change:+.1f}%)"
            )
            print(
                f"      Invisible without JS: {diff.content_invisible_without_js_percentage:.1f}%"
            )

            # Show text differences
            if diff.text_only_with_js:
                print(
                    f"\n    Content visible ONLY with JavaScript ({len(diff.text_only_with_js)} blocks):"
                )
                for block in diff.text_only_with_js[:5]:  # Show max 5 blocks
                    print(
                        f"      • {block[:100]}..."
                        if len(block) > 100
                        else f"      • {block}"
                    )
                if len(diff.text_only_with_js) > 5:
                    print(
                        f"      ... and {len(diff.text_only_with_js) - 5} more blocks"
                    )

            if diff.text_only_without_js:
                print(
                    f"\n    Content visible ONLY without JavaScript ({len(diff.text_only_without_js)} blocks):"
                )
                for block in diff.text_only_without_js[:5]:  # Show max 5 blocks
                    print(
                        f"      • {block[:100]}..."
                        if len(block) > 100
                        else f"      • {block}"
                    )
                if len(diff.text_only_without_js) > 5:
                    print(
                        f"      ... and {len(diff.text_only_without_js) - 5} more blocks"
                    )

            # Show heading differences
            if diff.headings_missing_without_js:
                print(
                    f"\n    Headings MISSING without JavaScript ({len(diff.headings_missing_without_js)}):"
                )
                for heading in diff.headings_missing_without_js[:5]:  # Show max 5
                    print(f"      • {heading}")
                if len(diff.headings_missing_without_js) > 5:
                    print(
                        f"      ... and {len(diff.headings_missing_without_js) - 5} more headings"
                    )

            # Show link differences
            if diff.internal_links_missing_without_js:
                print(
                    f"\n    Internal Links MISSING without JavaScript ({len(diff.internal_links_missing_without_js)}):"
                )
                for link in diff.internal_links_missing_without_js[:5]:  # Show max 5
                    print(f"      • {link['anchor_text']} -> {link['href']}")
                if len(diff.internal_links_missing_without_js) > 5:
                    print(
                        f"      ... and {len(diff.internal_links_missing_without_js) - 5} more links"
                    )

        print("\n" + "-" * 80 + "\n")

    # Show failed URLs if any
    failed_analyses = result.get_failed_analyses()
    if failed_analyses:
        print(f"\n{'=' * 80}")
        print(f"FAILED URLS ({len(failed_analyses)})")
        print(f"{'=' * 80}\n")

        for i, analysis in enumerate(failed_analyses, 1):
            print(f"[{i}] {analysis.url}")
            _print_errors(analysis)
            print("-" * 80 + "\n")


def _print_errors(analysis: URLAnalysis) -> None:
    """
    Print errors from an analysis in a readable format.

    Args:
        analysis: URLAnalysis containing errors
    """
    if analysis.fetch_errors:
        print("  Fetch Errors:")
        for error in analysis.fetch_errors:
            print(f"    • {error}")

    if analysis.render_errors:
        print("  Render Errors:")
        for error in analysis.render_errors:
            print(f"    • {error}")

    if analysis.extraction_errors:
        print("  Extraction Errors:")
        for error in analysis.extraction_errors:
            print(f"    • {error}")
