import json
import os
import time
from pathlib import Path

from pdf_scraper.scrape_pdfs import run_pdf_scraper

from schemas.pdf_scraper import PDFScrapeRequest, PDFScrapeResponse


def _resolve_output_path(output_path: Path) -> Path:
    if not output_path.is_absolute():
        base_dir = Path(os.environ.get("API_WORKDIR", "/code")).resolve()
        output_path = base_dir / output_path
    return output_path.resolve()


class PDFScraperService:
    @classmethod
    def run_scraper(cls, request: PDFScrapeRequest) -> PDFScrapeResponse:
        output_path_input = Path(request.output_path) if request.output_path else Path(
            f"pdf_results/output_{int(time.time())}.json"
        )
        output_path = _resolve_output_path(output_path_input)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        start_time = time.monotonic()
        try:
            results = run_pdf_scraper(
                start_url=str(request.start_url),
                max_pages=request.max_pages,
                delay=request.delay,
                keywords=request.require_keywords,
            )
            with open(output_path, "w", encoding="utf-8") as file:
                json.dump(results, file, indent=2)
            duration = time.monotonic() - start_time

            return PDFScrapeResponse(
                success=True,
                exit_code=0,
                output_path=str(output_path),
                stdout="OK",
                stderr="",
                duration_seconds=duration,
            )
        except Exception as exc: 
            duration = time.monotonic() - start_time
            return PDFScrapeResponse(
                success=False,
                exit_code=1,
                output_path=str(output_path),
                stdout="",
                stderr=str(exc),
                duration_seconds=duration,
            )
