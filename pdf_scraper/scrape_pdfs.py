"""
Reusable PDF scraper module (API-safe version).
This version is intended to be imported and executed inside a FastAPI service.

Original CLI logic was removed so it no longer runs sys.exit(), parses arguments,
or performs standalone execution.
"""

import logging
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


DEFAULT_HEADERS = {"User-Agent": "AdvisemePDFScraper/1.0"}
PDFTextChunk = Tuple[Optional[str], str]   # (title, text)


# --------------------------------------------------------
# Robots.txt Handler
# --------------------------------------------------------
class RobotsHandler:
    """Cache and evaluate robots.txt directives per domain."""

    def __init__(self, session: requests.Session, user_agent: str) -> None:
        self.session = session
        self.user_agent = user_agent
        self._cache: Dict[Tuple[str, str], Optional[RobotFileParser]] = {}

    def can_fetch(self, url: str) -> bool:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return True

        key = (parsed.scheme, parsed.netloc)
        if key not in self._cache:
            self._cache[key] = self._load_parser(parsed.scheme, parsed.netloc)

        parser = self._cache[key]
        if parser is None:
            return True

        try:
            return parser.can_fetch(self.user_agent, url)
        except Exception:
            return True

    def _load_parser(self, scheme: str, netloc: str) -> Optional[RobotFileParser]:
        robots_url = f"{scheme}://{netloc}/robots.txt"
        parser = RobotFileParser()
        parser.set_url(robots_url)

        try:
            resp = self.session.get(robots_url, timeout=10)
        except Exception:
            return None

        if resp.status_code == 200:
            parser.parse(resp.text.splitlines())
            parser.modified()
            return parser

        if resp.status_code in (401, 403):
            parser.parse(["User-agent: *", "Disallow: /"])
            parser.modified()
            return parser

        return None


# --------------------------------------------------------
# Core Helpers
# --------------------------------------------------------
def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    return parsed._replace(fragment="", path=path).geturl()


def is_same_domain(url: str, domain: str) -> bool:
    parsed = urlparse(url)
    return parsed.netloc == domain


# --------------------------------------------------------
# Crawl for PDFs
# --------------------------------------------------------
def crawl_for_pdfs(
    start_url: str,
    max_pages: int,
    request_delay: float,
    session: requests.Session,
    robots: RobotsHandler,
    keywords: Sequence[str],
) -> Set[str]:

    start_parsed = urlparse(start_url)
    domain = start_parsed.netloc
    start_url = normalize_url(start_url)

    to_visit = deque([start_url])
    queued = {start_url}
    seen = set()
    pdfs = set()

    while to_visit and len(seen) < max_pages:
        current = to_visit.popleft()
        queued.discard(current)

        if current in seen:
            continue

        if not robots.can_fetch(current):
            seen.add(current)
            continue

        try:
            resp = session.get(current, timeout=20)
            resp.raise_for_status()
        except Exception:
            continue

        seen.add(current)
        content_type = resp.headers.get("Content-Type", "")

        if "text/html" not in content_type:
            continue

        soup = BeautifulSoup(resp.text, "html.parser")

        for link in soup.find_all("a", href=True):
            resolved = normalize_url(urljoin(current, link["href"]))
            allowed = robots.can_fetch(resolved)
            lower = resolved.lower()

            if lower.endswith(".pdf"):
                if keywords and not any(k in lower for k in keywords):
                    continue
                if allowed:
                    pdfs.add(resolved)
                continue

            # Enqueue HTML pages within domain
            if (
                allowed and
                is_same_domain(resolved, domain) and
                resolved not in seen and
                resolved not in queued
            ):
                to_visit.append(resolved)
                queued.add(resolved)

        if request_delay > 0:
            time.sleep(request_delay)

    return pdfs


# --------------------------------------------------------
# PDF Extractor
# --------------------------------------------------------
def extract_pdf_title(pdf_bytes: BytesIO) -> Optional[str]:
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
    except Exception:
        pass
    finally:
        pdf_bytes.seek(0)
    return None


def extract_pdf_content(pdf_url: str, session: requests.Session) -> Dict:
    resp = session.get(pdf_url, timeout=60)
    resp.raise_for_status()

    pdf_bytes = BytesIO(resp.content)

    title = extract_pdf_title(pdf_bytes)

    try:
        text = extract_text(pdf_bytes)
    except Exception:
        text = ""

    return {"url": pdf_url, "title": title, "text": text}


# --------------------------------------------------------
# High-level function for API use
# --------------------------------------------------------
def run_pdf_scraper(
    start_url: str,
    max_pages: int = 100,
    delay: float = 1.0,
    keywords: Optional[Sequence[str]] = None,
) -> Dict[str, Dict]:
    """
    Main callable scraper function.
    Returns:  { pdf_url: {title: str, text: str} }
    """
    keywords = [k.lower() for k in (keywords or [])]

    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)
    robots = RobotsHandler(session, DEFAULT_HEADERS["User-Agent"])

    pdf_urls = crawl_for_pdfs(
        start_url,
        max_pages=max_pages,
        request_delay=delay,
        session=session,
        robots=robots,
        keywords=keywords,
    )

    results = {}
    for url in pdf_urls:
        try:
            results[url] = extract_pdf_content(url, session)
        except Exception as exc:
            results[url] = {"url": url, "title": None, "text": "", "error": str(exc)}

    return results
