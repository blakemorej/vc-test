# SEO Content Difference Tool

A CLI-first Python application that identifies content and SEO elements that differ when JavaScript is enabled vs disabled.

## Purpose

This tool helps SEO professionals, developers, and content strategists understand how JavaScript affects content visibility. It compares:

- **Raw HTML**: What non-JS crawlers (like some AI tools and basic bots) see
- **Rendered HTML**: What users and JS-capable crawlers (like modern search engines) see

### What It Does

✅ Identifies content visible only after JavaScript execution  
✅ Detects content missing when JavaScript is disabled  
✅ Finds SEO-relevant parity issues affecting non-JS crawlers  
✅ Reports heading and internal link differences  
✅ Exports results to CSV and JSON  

### What It Doesn't

❌ Not a full crawler  
❌ Not a Googlebot emulator  
❌ Not a rank tracking or performance tool  

## Installation

### Prerequisites

- Python 3.9 or higher
- pip package manager

### Install from Source

```bash
# Clone the repository
git clone https://github.com/yourusername/vc-test.git
cd vc-test

# Install dependencies
pip install -e ".[cli]"

# Install Playwright browsers
playwright install chromium
```

### Verify Installation

```bash
seo-diff --help
```

## Usage

### Basic Usage

Create a text file with one URL per line:

```bash
# urls.txt
https://example.com/page1
https://example.com/page2
https://example.com/blog/post
```

Run the tool:

```bash
seo-diff urls.txt
```

### Advanced Usage

```bash
# Specify output directory and format
seo-diff urls.txt -o ./results -f json

# Increase concurrency and timeout
seo-diff urls.txt --concurrency 5 --timeout 60

# Use different wait strategy for JS rendering
seo-diff urls.txt --wait-strategy load

# Custom user agent
seo-diff urls.txt --user-agent "Mozilla/5.0 CustomBot/1.0"
```

### Command-Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `input_file` | Text file with one URL per line | Required |
| `-o, --output-dir` | Directory to save output files | `.` |
| `-f, --format` | Output format (`csv` or `json`) | `csv` |
| `-c, --concurrency` | Max concurrent URLs to process | `3` |
| `-t, --timeout` | Timeout in seconds per fetch | `30` |
| `-w, --wait-strategy` | JS render wait strategy | `network_idle` |
| `--user-agent` | Custom User-Agent header | Auto-generated |

## Output

### Terminal Output

The CLI displays a human-readable summary showing:

- Overall statistics (processed, succeeded, failed)
- URLs with detected differences
- Detailed difference reports:
  - Word count metrics and percentages
  - Content unique to each version
  - Missing headings and internal links
- Error details for failed URLs

### CSV Output

Optimized for spreadsheet import and human readability:

```csv
# SEO Content Difference Report
# Generated: 2024-01-15 10:30:00
# URLs Processed: 5
# URLs Succeeded: 4
# URLs Failed: 1
# Success Rate: 80.00%

URL,Final URL,HTTP Status,Raw Word Count,Rendered Word Count,Word Count Delta,Content Invisible Without JS (%),Headings Missing Without JS,Internal Links Missing Count,Success,Errors
https://example.com,https://example.com,200,2450,3120,+670,27.3,Welcome to Example,5,Yes,
```

### JSON Output

Full data structure for programmatic access and API integration:

```json
{
  "metadata": {
    "started_at": "2024-01-15T10:30:00",
    "finished_at": "2024-01-15T10:30:45",
    "urls_processed": 5,
    "urls_succeeded": 4,
    "urls_failed": 1,
    "success_rate": 80.0
  },
  "results": [
    {
      "url": "https://example.com",
      "final_url": "https://example.com",
      "http_status": 200,
      "raw_word_count": 2450,
      "rendered_word_count": 3120,
      "word_count_delta": 670,
      "content_invisible_without_js_percentage": 27.3,
      "headings_missing_without_js": ["Welcome to Example"],
      "internal_links_missing_count": 5,
      "differences": {
        "text_only_with_js": ["block 1", "block 2"],
        "text_only_without_js": [],
        "headings_missing_without_js": ["Welcome to Example"],
        "headings_extra_without_js": [],
        "internal_links_missing_without_js": [
          {"href": "/about", "anchor_text": "About Us"}
        ],
        "internal_links_extra_without_js": []
      },
      "success": true
    }
  ]
}
```

## Architecture

### Engine-First Design

The tool is architected with a **reusable core engine** that can be called from:

- ✅ CLI today
- ✅ Web API in the future (without refactoring)

### Thin CLI

The CLI is a thin wrapper that:

1. Accepts input (file, flags)
2. Calls engine functions
3. Outputs results

**No business logic lives in the CLI.**

### Core Engine Components

```
engine/
├── models.py          # Data classes (URLAnalysis, JobResult, etc.)
├── fetcher.py         # RawHTMLFetcher + JSRenderedFetcher
├── extractor.py       # Content extraction (no HTML diff!)
├── differ.py          # Content comparison logic
├── job_runner.py      # Orchestration pipeline
└── storage.py         # Abstract storage interface + FileStorage
```

### Key Design Principles

1. **Engine-first**: All logic in reusable core engine
2. **Thin CLI**: CLI is just an input/output adapter
3. **Explicit over clever**: Clear, readable code
4. **Abstract storage**: File storage today, database tomorrow
5. **Fail per-URL**: Errors don't crash entire run

## Technology Stack

### Core Engine
- **httpx** - Async HTTP client
- **beautifulsoup4** - HTML parsing
- **playwright** - Headless browser for JS rendering
- **lxml** - Fast parser

### CLI (Optional)
- **rich** - Pretty terminal output

## Development

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/yourusername/vc-test.git
cd vc-test

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev,cli]"

# Install Playwright browsers
playwright install chromium
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_fetcher.py
```

### Code Quality

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Lint
ruff check src/ tests/

# Type checking
mypy src/
```

## Future Roadmap

### Planned Features

- [ ] Web API endpoints (FastAPI/Flask)
- [ ] Database storage (PostgreSQL)
- [ ] Job queue (Redis/Celery)
- [ ] Web UI for viewing results
- [ ] Scheduling and history
- [ ] Authentication and billing (SaaS)

### Future-Proofing

The engine is designed for **zero refactor** when transitioning to a web app:

- All models can become Pydantic models for API responses
- `JobRunner.run_job()` → API endpoint
- `Storage` interface → Swap for database implementation
- CLI completely isolated from engine

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run tests and linting
6. Submit a pull request

### Development Guidelines

- Keep CLI thin - put all logic in engine
- Write tests for new features
- Follow existing code style
- Update documentation

## License

MIT License - See LICENSE file for details

## Support

For issues, questions, or suggestions:

- GitHub Issues: WIP
- Documentation: WIP

---

**Built for SEO professionals who need to understand JavaScript's impact on content visibility.**
