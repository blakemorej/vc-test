"""
Storage layer for persisting job results.

Provides abstract interface for storage backends and file-based implementations
for CSV and JSON export.
"""

import csv
import json
from abc import ABC, abstractmethod
from pathlib import Path

from .models import JobResult


class StorageError(Exception):
    """Base exception for storage errors."""

    pass


class Storage(ABC):
    """
    Abstract interface for storage backends.

    Designed to be swappable - can be replaced with database storage
    for future web application without changing engine code.
    """

    @abstractmethod
    def save(self, result: JobResult, format: str = "csv", output_path: str | None = None) -> str:
        """
        Save job results to storage.

        Args:
            result: JobResult to save
            format: Output format ('csv' or 'json')
            output_path: Optional output file path. If not provided, generates one.

        Returns:
            Path to the saved file (for file storage) or identifier (for database)

        Raises:
            StorageError: If save operation fails
        """
        pass


class FileStorage(Storage):
    """
    File-based storage implementation.

    Exports results to CSV or JSON files. Designed for CLI usage but can be
    easily replaced by database storage for web application.
    """

    def __init__(self, output_directory: str = "."):
        """
        Initialize file storage.

        Args:
            output_directory: Directory to save output files (default: current directory)
        """
        self.output_directory = Path(output_directory)
        self.output_directory.mkdir(parents=True, exist_ok=True)

    def save(self, result: JobResult, format: str = "csv", output_path: str | None = None) -> str:
        """
        Save job results to file.

        Args:
            result: JobResult to save
            format: Output format ('csv' or 'json')
            output_path: Optional output file path. If not provided, generates one.

        Returns:
            Path to the saved file

        Raises:
            StorageError: If save operation fails
        """
        format_lower = format.lower()

        if format_lower not in ("csv", "json"):
            raise StorageError(f"Unsupported format: {format}. Use 'csv' or 'json'.")

        # Generate output path if not provided
        if output_path is None:
            timestamp = result.started_at.strftime("%Y%m%d_%H%M%S")
            output_path = f"seo_diff_results_{timestamp}.{format_lower}"

        output_file_path = self.output_directory / output_path

        try:
            if format_lower == "csv":
                self._save_csv(result, output_file_path)
            else:  # json
                self._save_json(result, output_file_path)

            return str(output_file_path)

        except Exception as e:
            raise StorageError(f"Failed to save results: {str(e)}")

    def _save_csv(self, result: JobResult, output_path: Path):
        """
        Save results to CSV format.

        CSV format is optimized for human readability and spreadsheet import.
        Includes summary information and one row per URL.

        Args:
            result: JobResult to save
            output_path: Path to save CSV file
        """
        with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
            # Write summary header
            csvfile.write(f"# SEO Content Difference Report\n")
            csvfile.write(f"# Generated: {result.finished_at}\n")
            csvfile.write(f"# URLs Processed: {result.urls_processed}\n")
            csvfile.write(f"# URLs Succeeded: {result.urls_succeeded}\n")
            csvfile.write(f"# URLs Failed: {result.urls_failed}\n")
            csvfile.write(f"# Success Rate: {result.success_rate}%\n")
            csvfile.write("\n")

            # CSV headers
            fieldnames = [
                "URL",
                "Final URL",
                "HTTP Status",
                "Raw Word Count",
                "Rendered Word Count",
                "Word Count Delta",
                "Content Invisible Without JS (%)",
                "Headings Missing Without JS",
                "Internal Links Missing Count",
                "Success",
                "Errors",
            ]

            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            # Write one row per URL analysis
            for analysis in result.results:
                diff = analysis.differences

                row = {
                    "URL": analysis.url,
                    "Final URL": analysis.final_url,
                    "HTTP Status": analysis.http_status,
                    "Raw Word Count": diff.raw_word_count if diff else 0,
                    "Rendered Word Count": diff.rendered_word_count if diff else 0,
                    "Word Count Delta": diff.word_count_delta if diff else 0,
                    "Content Invisible Without JS (%)": diff.content_invisible_without_js_percentage
                    if diff
                    else 0.0,
                    "Headings Missing Without JS": ", ".join(
                        diff.headings_missing_without_js if diff else []
                    ),
                    "Internal Links Missing Count": len(
                        diff.internal_links_missing_without_js if diff else []
                    ),
                    "Success": "Yes" if analysis.success else "No",
                    "Errors": self._format_errors(analysis),
                }

                writer.writerow(row)

    def _save_json(self, result: JobResult, output_path: Path):
        """
        Save results to JSON format.

        JSON format includes full data structure for programmatic access
        and API integration.

        Args:
            result: JobResult to save
            output_path: Path to save JSON file
        """
        data = {
            "metadata": {
                "started_at": result.started_at.isoformat(),
                "finished_at": result.finished_at.isoformat() if result.finished_at else None,
                "urls_processed": result.urls_processed,
                "urls_succeeded": result.urls_succeeded,
                "urls_failed": result.urls_failed,
                "success_rate": result.success_rate,
            },
            "results": [],
        }

        # Convert each analysis to dict
        for analysis in result.results:
            analysis_dict = analysis.to_dict()

            # Add full difference details
            if analysis.differences:
                analysis_dict["differences"] = {
                    "text_only_with_js": analysis.differences.text_only_with_js,
                    "text_only_without_js": analysis.differences.text_only_without_js,
                    "headings_missing_without_js": analysis.differences.headings_missing_without_js,
                    "headings_extra_without_js": analysis.differences.headings_extra_without_js,
                    "internal_links_missing_without_js": analysis.differences.internal_links_missing_without_js,
                    "internal_links_extra_without_js": analysis.differences.internal_links_extra_without_js,
                }

            data["results"].append(analysis_dict)

        # Write JSON with pretty printing
        with open(output_path, "w", encoding="utf-8") as jsonfile:
            json.dump(data, jsonfile, indent=2, ensure_ascii=False)

    def _format_errors(self, analysis) -> str:
        """
        Format errors from analysis into a readable string.

        Args:
            analysis: URLAnalysis object

        Returns:
            Comma-separated list of errors
        """
        all_errors = []

        if analysis.fetch_errors:
            all_errors.extend([f"Fetch: {e}" for e in analysis.fetch_errors])
        if analysis.render_errors:
            all_errors.extend([f"Render: {e}" for e in analysis.render_errors])
        if analysis.extraction_errors:
            all_errors.extend([f"Extraction: {e}" for e in analysis.extraction_errors])

        return "; ".join(all_errors)
