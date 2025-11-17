from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool

from schemas.pdf_scraper import PDFScrapeRequest, PDFScrapeResponse
from services.pdf_scraper_service import PDFScraperService

router = APIRouter(
    prefix="/pdf-scraper",
    tags=["pdf-scraper"],
)


@router.post("/", response_model=PDFScrapeResponse)
async def trigger_pdf_scraper(payload: PDFScrapeRequest) -> PDFScrapeResponse:
    """
    Trigger the PDF scraper synchronously using the provided configuration.
    """
    try:
        result = await run_in_threadpool(PDFScraperService.run_scraper, payload)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Failed to start PDF scraper: {exc}") from exc

    if not result.success:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "PDF scraper completed with errors.",
                "exit_code": result.exit_code,
                "stderr": result.stderr,
            },
        )

    return result
