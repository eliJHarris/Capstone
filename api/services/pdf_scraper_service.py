import os
import subprocess
import sys
import time
from pathlib import Path
from typing import List

from schemas.pdf_scraper import PDFScrapeRequest, PDFScrapeResponse


def _resolve_output_path(output_path: Path) -> Path:
    """
    Resolve an output path ensuring that relative paths live under the working directory.
    """
    if not output_path.is_absolute():
        # Default to the FastAPI application directory when relative paths are given.
        base_dir = Path(os.environ.get("API_WORKDIR", "/code")).resolve()
        output_path = base_dir / output_path
    return output_path.resolve()


def _build_command(request: PDFScrapeRequest, script_path: Path, output_path: Path) -> List[str]:
    """Convert a request payload into CLI arguments for the scraper."""
    command: List[str] = [
        sys.executable,
        str(script_path),
        str(request.start_url),
        "--output",
        str(output_path),
        "--max-pages",
        str(request.max_pages),
        "--delay",
        str(request.delay),
        "--timeout",
        str(request.timeout),
    ]

    if request.verbose:
        command.append("--verbose")

    for keyword in request.require_keywords:
        command.extend(["--require-keyword", keyword])

    return command


class PDFScraperService:
    """Service wrapper for invoking the standalone PDF scraper."""

    @staticmethod
    def _script_path() -> Path:
        candidate = os.environ.get("PDF_SCRAPER_PATH", "/pdf_scraper/scrape_pdfs.py")
        script_path = Path(candidate).resolve()
        return script_path

    @classmethod
    def run_scraper(cls, request: PDFScrapeRequest) -> PDFScrapeResponse:
        script_path = cls._script_path()
        if not script_path.exists():
            raise FileNotFoundError(
                f"PDF scraper script not found at {script_path}. Check docker-compose volume mounts."
            )

        output_path_input = Path(request.output_path) if request.output_path else Path(
            f"pdf_results/output_{int(time.time())}.txt"
        )
        output_path = _resolve_output_path(output_path_input)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        command = _build_command(request, script_path, output_path)

        start_time = time.monotonic()
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
        )
        duration = time.monotonic() - start_time

        return PDFScrapeResponse(
            success=process.returncode == 0,
            exit_code=process.returncode,
            output_path=str(output_path),
            stdout=process.stdout or "",
            stderr=process.stderr or "",
            duration_seconds=duration,
        )
