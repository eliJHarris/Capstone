import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from typing import Dict, Optional
from uuid import uuid4

from schemas.pdf_scraper import (
    PDFScrapeJobDetail,
    PDFScrapeJobStatus,
    PDFScrapeJobSummary,
    PDFScrapeRequest,
    PDFScrapeResponse,
)
from services.pdf_scraper_service import PDFScraperService


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class _JobRecord:
    request: PDFScrapeRequest
    status: PDFScrapeJobStatus
    created_at: datetime
    updated_at: datetime
    result: Optional[PDFScrapeResponse] = None
    error: Optional[str] = None


_jobs: Dict[str, _JobRecord] = {}
_lock = Lock()
_executor = ThreadPoolExecutor(max_workers=int(os.environ.get("PDF_SCRAPER_MAX_WORKERS", "2")))


def submit_job(request: PDFScrapeRequest) -> PDFScrapeJobSummary:
    job_id = uuid4().hex
    created_at = _now()
    record = _JobRecord(
        request=request.model_copy(deep=True),
        status=PDFScrapeJobStatus.pending,
        created_at=created_at,
        updated_at=created_at,
    )
    with _lock:
        _jobs[job_id] = record

    _executor.submit(_run_job, job_id)

    return _to_summary(job_id, record)


def get_job_summary(job_id: str) -> PDFScrapeJobSummary:
    record = _get_job(job_id)
    return _to_summary(job_id, record)


def get_job_detail(job_id: str) -> PDFScrapeJobDetail:
    record = _get_job(job_id)
    return _to_detail(job_id, record)


def _run_job(job_id: str) -> None:
    record = _get_job(job_id)
    _update_record(job_id, status=PDFScrapeJobStatus.running)

    try:
        result = PDFScraperService.run_scraper(record.request)
    except Exception as exc:  # noqa: BLE001
        _update_record(job_id, status=PDFScrapeJobStatus.failed, error=str(exc))
        return

    if result.success:
        _update_record(job_id, status=PDFScrapeJobStatus.succeeded, result=result)
    else:
        error_message = (
            f"Scraper finished with exit code {result.exit_code}. Stderr: {result.stderr.strip()}"
            if result.stderr
            else f"Scraper finished with exit code {result.exit_code}."
        )
        _update_record(
            job_id,
            status=PDFScrapeJobStatus.failed,
            result=result,
            error=error_message,
        )


def _update_record(
    job_id: str,
    *,
    status: Optional[PDFScrapeJobStatus] = None,
    result: Optional[PDFScrapeResponse] = None,
    error: Optional[str] = None,
) -> None:
    with _lock:
        record = _jobs[job_id]
        if status is not None:
            record.status = status
        if result is not None:
            record.result = result
        if error is not None:
            record.error = error
        record.updated_at = _now()


def _get_job(job_id: str) -> _JobRecord:
    with _lock:
        if job_id not in _jobs:
            raise KeyError(job_id)
        return _jobs[job_id]


def _to_summary(job_id: str, record: _JobRecord) -> PDFScrapeJobSummary:
    return PDFScrapeJobSummary(
        job_id=job_id,
        status=record.status,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _to_detail(job_id: str, record: _JobRecord) -> PDFScrapeJobDetail:
    return PDFScrapeJobDetail(
        job_id=job_id,
        status=record.status,
        created_at=record.created_at,
        updated_at=record.updated_at,
        request=record.request,
        result=record.result,
        error=record.error,
    )
