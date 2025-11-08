#!/usr/bin/env python3
"""Domain PDF scraper."""
import argparse
import logging
import sys
import time
from collections import deque
from io import BytesIO
from pathlib import Path
from typing import Dict, Iterable, Optional, Sequence, Set, Tuple
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup
from pdfminer.high_level import extract_text
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfparser import PDFParser

DEFAULT_HEADERS = {
    "User-Agent": "CapstonePDFScraper/1.0 (+https://github.com/)",
}

# A tuple makes this a lightweight, immutable pair (title, text) for each PDF.
PDFTextChunk = Tuple[Optional[str], str]


class RobotsHandler:
    """Cache and evaluate robots.txt directives per domain."""

    def __init__(self, session: requests.Session, user_agent: str) -> None:
        self.session = session
        self.user_agent = user_agent or "*"
        # Cache RobotFileParser instances so each site's robots.txt is fetched once.
        self._parsers: Dict[Tuple[str, str], Optional[RobotFileParser]] = {}

    def can_fetch(self, url: str) -> bool:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return True

        key = (parsed.scheme, parsed.netloc)
        if key not in self._parsers:
            self._parsers[key] = self._load_parser(parsed.scheme, parsed.netloc)

        parser = self._parsers[key]
        if parser is None:
            return True

        try:
            return parser.can_fetch(self.user_agent, url)
        except Exception as exc:  # noqa: BLE001
            logging.debug("Robots evaluation failed for %s (%s)", url, exc)
            return True

    def _load_parser(self, scheme: str, netloc: str) -> Optional[RobotFileParser]:
        robots_url = f"{scheme}://{netloc}/robots.txt"
        parser = RobotFileParser()
        parser.set_url(robots_url)

        try:
            response = self.session.get(robots_url, timeout=10)
        except Exception as exc:  # noqa: BLE001
            logging.debug("Unable to fetch robots.txt at %s (%s)", robots_url, exc)
            return None

        if response.status_code == 200:
            parser.parse(response.text.splitlines())
            parser.modified()
            return parser

        if response.status_code in (401, 403):
            # Respect explicit disallow-all responses to keep us out.
            parser.parse(["User-agent: *", "Disallow: /"])
            parser.modified()
            return parser

        logging.debug(
            "Robots.txt not available at %s (status %s). Assuming allow all.",
            robots_url,
            response.status_code,
        )
        return None


def is_same_domain(url: str, domain: str) -> bool:
    """Return True if `url` belongs to `domain`."""
    parsed = urlparse(url)
    return parsed.netloc == domain


def normalize_url(url: str) -> str:
    """Normalize URLs by removing fragments and redundant trailing slashes."""
    parsed = urlparse(url)
    # Ensure directories use a canonical slash style while keeping file paths intact.
    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    normalized = parsed._replace(fragment="", path=path)
    return normalized.geturl()


def crawl_for_pdfs(
    start_url: str,
    max_pages: int,
    request_delay: float,
    session: requests.Session,
    robots: RobotsHandler,
    keywords: Sequence[str],
) -> Set[str]:
    """Breadth-first crawl within the start domain to collect PDF URLs."""
    start_parsed = urlparse(start_url)
    domain = start_parsed.netloc

    start_url = normalize_url(start_url)
    # BFS queue plus helper sets keep us from visiting the same page twice.
    to_visit = deque([start_url])
    queued_pages: Set[str] = {start_url}
    seen_pages: Set[str] = set()
    pdf_urls: Set[str] = set()

    # Stop when the queue is empty or we've hit the crawl limit.
    while to_visit and len(seen_pages) < max_pages:
        current_url = to_visit.popleft()
        queued_pages.discard(current_url)
        if current_url in seen_pages:
            continue

        if not robots.can_fetch(current_url):
            logging.info("Skipping %s (disallowed by robots.txt)", current_url)
            seen_pages.add(current_url)
            continue

        logging.info("Fetching page: %s", current_url)
        try:
            response = session.get(current_url, timeout=20)
            response.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            logging.warning("Skipping %s (%s)", current_url, exc)
            continue

        seen_pages.add(current_url)

        content_type = response.headers.get("Content-Type", "")
        if "text/html" not in content_type:
            logging.debug("Non-HTML content at %s (%s)", current_url, content_type)
            continue

        soup = BeautifulSoup(response.text, "html.parser")
        # Walk every anchor tag so we consider both HTML pages and PDFs.
        for link in soup.find_all("a", href=True):
            resolved = urljoin(current_url, link["href"])
            resolved = normalize_url(resolved)
            # Decide once per link if robots permits us to visit or download it.
            resolved_lower = resolved.lower()
            allowed_by_robots = robots.can_fetch(resolved)

            if resolved_lower.endswith(".pdf"):
                # Apply optional keyword filter before saving the PDF URL.
                if keywords and not any(keyword in resolved_lower for keyword in keywords):
                    logging.debug(
                        "Skipping PDF %s (URL did not match keywords: %s)",
                        resolved,
                        ", ".join(keywords),
                    )
                    continue
                if not allowed_by_robots:
                    logging.info(
                        "Skipping PDF %s (disallowed by robots.txt)",
                        resolved,
                    )
                    continue
                if resolved not in pdf_urls:
                    pdf_urls.add(resolved)
                    logging.info("Found PDF: %s", resolved)
                continue

            # Only enqueue HTML pages that stay within the starting domain.
            if (
                is_same_domain(resolved, domain)
                and resolved not in seen_pages
                and resolved not in queued_pages
                and allowed_by_robots
            ):
                to_visit.append(resolved)
                queued_pages.add(resolved)
            elif is_same_domain(resolved, domain) and not allowed_by_robots:
                logging.debug("Skipping %s (disallowed by robots.txt)", resolved)

        if request_delay:
            # Throttle requests to avoid hammering servers.
            time.sleep(request_delay)

    return pdf_urls


def extract_pdf_content(pdf_url: str, session: requests.Session) -> Tuple[Optional[str], str]:
    """Download a PDF and return its title metadata and extracted text."""
    logging.info("Downloading PDF: %s", pdf_url)
    response = session.get(pdf_url, timeout=60)
    response.raise_for_status()

    pdf_bytes = BytesIO(response.content)
    title = extract_pdf_title(pdf_bytes)
    # Reuse the same BytesIO so pdfminer can rewind between reads.
    try:
        text = extract_text(pdf_bytes)
    except Exception as exc:  # noqa: BLE001
        logging.error("Failed to extract text from %s (%s)", pdf_url, exc)
        return title, ""
    finally:
        pdf_bytes.close()
    return title, text


def save_text_chunks(chunks: Iterable[PDFTextChunk], output_path: Path) -> None:
    """Append each chunk of text to the output file with separators."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for idx, (title, chunk) in enumerate(chunks, start=1):
            if not chunk.strip():
                continue
            handle.write(f"----- PDF {idx} START -----\n")
            if title:
                handle.write(f"Title: {title}\n")
            handle.write(chunk)
            handle.write(f"\n----- PDF {idx} END -----\n\n")


def configure_logging(verbose: bool) -> None:
    """Configure basic logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s:%(message)s")


def extract_pdf_title(pdf_bytes: BytesIO) -> Optional[str]:
    """Return the PDF title metadata if available."""
    try:
        pdf_bytes.seek(0)
        parser = PDFParser(pdf_bytes)
        doc = PDFDocument(parser)
        info = doc.info or []
        for entry in info:
            title = entry.get("Title")
            if title:
                if isinstance(title, bytes):
                    return title.decode("utf-8", errors="ignore").strip()
                return str(title).strip()
    except Exception as exc:  # noqa: BLE001
        logging.debug("Unable to read PDF title (%s)", exc)
    finally:
        pdf_bytes.seek(0)
    return None


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    """Define and parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Crawl a domain for PDFs, extract their text, and combine it.",
    )
    parser.add_argument(
        "start_url",
        help="Starting URL (e.g., https://example.com) to begin the crawl.",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="pdf_text_collection.txt",
        help="Output text file path (default: pdf_text_collection.txt).",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=200,
        help="Maximum number of HTML pages to crawl (default: 200).",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay in seconds between requests to avoid stressing servers (default: 1.0).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=20,
        help="HTTP timeout in seconds for page fetches (default: 20).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Increase log output for debugging.",
    )
    parser.add_argument(
        "--require-keyword",
        action="append",
        default=[],
        metavar="TERM",
        help="Only include PDFs whose URL contains at least one of the provided keywords. "
        "Repeat the flag for multiple keywords.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Iterable[str]] = None) -> int:
    """Entry point when run as a script."""
    args = parse_args(list(argv) if argv is not None else sys.argv[1:])
    configure_logging(args.verbose)

    # Session keeps connections alive and shares headers.
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)
    robots = RobotsHandler(session=session, user_agent=session.headers.get("User-Agent", "*"))
    # Normalize keyword filters once.
    keywords = [keyword.lower() for keyword in args.require_keyword]

    logging.info("Starting crawl at %s", args.start_url)
    pdf_urls = crawl_for_pdfs(
        args.start_url,
        max_pages=args.max_pages,
        request_delay=max(args.delay, 0.0),
        session=session,
        robots=robots,
        keywords=keywords,
    )

    if not pdf_urls:
        logging.warning("No PDFs found at %s", args.start_url)
        return 1

    logging.info("Found %d PDFs. Beginning extraction.", len(pdf_urls))
    text_chunks: list[PDFTextChunk] = []

    for pdf_url in sorted(pdf_urls):
        if not robots.can_fetch(pdf_url):
            logging.info(
                "Skipping PDF %s (disallowed by robots.txt)",
                pdf_url,
            )
            continue
        try:
            title, text = extract_pdf_content(pdf_url, session=session)
        except Exception as exc:  # noqa: BLE001
            logging.error("Skipping PDF %s due to unexpected error: %s", pdf_url, exc)
            continue
        if text.strip():
            text_chunks.append((title, text))
        else:
            logging.warning("No extractable text found in %s", pdf_url)

    if not text_chunks:
        logging.warning("No text could be extracted from the collected PDFs.")
        return 1

    # Resolve to an absolute path for clearer logs.
    output_path = Path(args.output).expanduser().resolve()
    save_text_chunks(text_chunks, output_path)
    logging.info("Combined text written to %s", output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
