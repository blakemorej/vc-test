"""
CLI main entry point for SEO Content Difference Tool.

Thin wrapper around the core engine - no business logic here.
"""

import argparse
import sys
from pathlib import Path

from engine import JobRunner
from engine.storage import FileStorage

from .output import print_results_summary


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments.

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="Compare content between JavaScript-enabled and JavaScript-disabled versions of web pages.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s urls.txt
  %(prog)s urls.txt -o ./results
  %(prog)s urls.txt --format json
  %(prog)s urls.txt --concurrency 5 --timeout 60
        """,
    )

    parser.add_argument(
        "input_file",
        type=str,
        help="Text file containing one URL per line",
    )

    parser.add_argument(
        "-o",
        "--output-dir",
        type=str,
        default=".",
        help="Directory to save output files (default: current directory)",
    )

    parser.add_argument(
        "-f",
        "--format",
        type=str,
        choices=["csv", "json"],
        default="csv",
        help="Output format (default: csv)",
    )

    parser.add_argument(
        "-c",
        "--concurrency",
        type=int,
        default=3,
        help="Maximum number of URLs to process concurrently (default: 3)",
    )

    parser.add_argument(
        "-t",
        "--timeout",
        type=int,
        default=30,
        help="Timeout in seconds for each fetch/render (default: 30)",
    )

    parser.add_argument(
        "-w",
        "--wait-strategy",
        type=str,
        choices=["network_idle", "load", "timeout"],
        default="network_idle",
        help="Wait strategy for JS rendering (default: network_idle)",
    )

    parser.add_argument(
        "--user-agent",
        type=str,
        default=None,
        help="Custom User-Agent header (optional)",
    )

    return parser.parse_args()


def read_urls_from_file(input_file: str) -> list[str]:
    """
    Read URLs from input file.

    Args:
        input_file: Path to input file

    Returns:
        List of URLs

    Raises:
        SystemExit: If file cannot be read
    """
    try:
        file_path = Path(input_file)

        if not file_path.exists():
            print(f"Error: File not found: {input_file}", file=sys.stderr)
            sys.exit(1)

        with open(file_path, "r", encoding="utf-8") as f:
            urls = [line.strip() for line in f if line.strip()]

        if not urls:
            print(f"Error: No URLs found in {input_file}", file=sys.stderr)
            sys.exit(1)

        return urls

    except Exception as e:
        print(f"Error reading file {input_file}: {e}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    """
    Main CLI entry point.

    Orchestrates the entire CLI workflow:
    1. Parse arguments
    2. Read URLs from file
    3. Run engine job
    4. Display results
    5. Save results to file
    """
    args = parse_arguments()

    # Read URLs from input file
    print(f"Reading URLs from: {args.input_file}")
    urls = read_urls_from_file(args.input_file)
    print(f"Found {len(urls)} URLs to process\n")

    # Create job runner with configuration
    runner = JobRunner(
        max_concurrency=args.concurrency,
        fetch_timeout=args.timeout * 1000,  # Convert to milliseconds
        render_timeout=args.timeout * 1000,  # Convert to milliseconds
        user_agent=args.user_agent,
        wait_strategy=args.wait_strategy,
    )

    # Run the job
    print("Processing URLs...")
    result = runner.run_job(urls)

    # Display results summary in terminal
    print_results_summary(result)

    # Save results to file
    print(f"\nSaving results to {args.format.upper()} file...")
    storage = FileStorage(output_directory=args.output_dir)

    try:
        output_path = storage.save(result, format=args.format)
        print(f"✓ Results saved to: {output_path}")
    except Exception as e:
        print(f"✗ Failed to save results: {e}", file=sys.stderr)
        sys.exit(1)

    # Exit with error code if any URLs failed
    if result.urls_failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
