from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool

from dependencies.auth import require_user
from schemas.pdf_scraper import PDFScrapeRequest, PDFScrapeResponse
from services.pdf_scraper_service import PDFScraperService

router = APIRouter(
    prefix="/pdf-scraper",
    tags=["pdf-scraper"],
)


@router.post("/", response_model=PDFScrapeResponse)
async def trigger_pdf_scraper(
    payload: PDFScrapeRequest,
    user=Depends(require_user),
) -> PDFScrapeResponse:
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


@router.post("", response_model=PDFScrapeResponse, include_in_schema=False)
async def trigger_pdf_scraper_no_slash(
    payload: PDFScrapeRequest,
    user=Depends(require_user),
) -> PDFScrapeResponse:
    """
    Compatibility handler so callers hitting /pdf-scraper without the trailing slash
    don't get redirected (which breaks CORS preflight in browsers).
    """
    return await trigger_pdf_scraper(payload, user)
