from fastapi import APIRouter, HTTPException

from schemas.pdf_scraper import (
    PDFScrapeJobDetail,
    PDFScrapeJobSummary,
    PDFScrapeRequest,
)
from services import pdf_scraper_jobs

router = APIRouter(
    prefix="/pdf-scraper",
    tags=["pdf-scraper"],
)


@router.post("/", response_model=PDFScrapeJobSummary, status_code=202)
async def trigger_pdf_scraper(payload: PDFScrapeRequest) -> PDFScrapeJobSummary:
    """
    Enqueue a PDF scraping job using the provided configuration.
    """
    try:
        return pdf_scraper_jobs.submit_job(payload)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/jobs", response_model=PDFScrapeJobSummary, status_code=202, include_in_schema=False)
async def trigger_pdf_scraper_alias(payload: PDFScrapeRequest) -> PDFScrapeJobSummary:
    """
    Backwards-compatible alias for submitting a PDF scraper job.
    """
    return await trigger_pdf_scraper(payload)


@router.get("/jobs/{job_id}", response_model=PDFScrapeJobDetail)
async def get_pdf_scraper_job(job_id: str) -> PDFScrapeJobDetail:
    """
    Retrieve the current status (and eventual results) of a PDF scraping job.
    """
    try:
        return pdf_scraper_jobs.get_job_detail(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Job {job_id} was not found.") from exc
