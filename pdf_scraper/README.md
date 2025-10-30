# PDF Domain Scraper

Python utility to crawl a domain for PDF links, extract their text, and collect
the combined output into a single text file.

## Requirements

Install the dependencies with:

```bash
pip install -r requirements.txt
```

The script relies on the open-source packages `requests`, `beautifulsoup4`, and
`pdfminer.six`.

## Usage

```bash
python scrape_pdfs.py https://example.com --output combined.txt
```

Key options:

- `--max-pages`: cap the number of HTML pages to visit (default 200).
- `--delay`: pause in seconds between requests for polite crawling (default 1.0).
- `--verbose`: enable detailed logs for troubleshooting.
- `--require-keyword TERM`: only keep PDFs whose metadata title contains at least one keyword; repeat the flag for multiple terms.

Results are written to the output file with clear separators between PDFs.

## Docker

Build the image:

```bash
docker build -t pdf-scraper .
```

Run the scraper (mount a host directory to collect the output):

```bash
docker run --rm -v "$PWD:/data" pdf-scraper https://example.com --output /data/combined.txt
```

Replace the URL and output path as needed; any arguments after the image name are forwarded to the script.

### Helper script

An interactive helper is available:

```bash
./run_scraper.sh
```

It prompts for the target domain/URL, desired output filename, and optional comma-separated keywords (matched against PDF titles), builds the Docker image if needed, and runs the scraper with sensible defaults.

## Notes

- Only URLs on the same host as the starting URL are crawled.
- Respect the target site's robots.txt and terms of service before running the scraper.
- Some PDFs may not yield extractable text (e.g., scanned images without OCR).
