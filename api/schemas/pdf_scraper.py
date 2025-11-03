from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator


class PDFScrapeRequest(BaseModel):
    start_url: HttpUrl = Field(..., description="Starting URL to begin crawling for PDFs.")
    output_path: Optional[str] = Field(
        None,
        description="Optional path for the output text file. Relative paths resolve under the API working directory.",
    )
    max_pages: int = Field(
        200,
        ge=1,
        description="Maximum number of HTML pages to crawl before stopping.",
    )
    delay: float = Field(
        1.0,
        ge=0.0,
        description="Delay in seconds between HTTP requests to avoid stressing servers.",
    )
    timeout: int = Field(
        20,
        ge=1,
        description="HTTP timeout in seconds for individual page fetches.",
    )
    verbose: bool = Field(
        False,
        description="Enable verbose logging from the scraper.",
    )
    require_keywords: List[str] = Field(
        default_factory=list,
        description="Only include PDFs whose URL contains at least one of these keywords.",
    )

    @field_validator("start_url", mode="before")
    @classmethod
    def _normalize_start_url(cls, value: str) -> str:
        """Allow callers to omit the scheme by defaulting to https."""
        if isinstance(value, str) and not value.startswith(("http://", "https://")):
            return f"https://{value}"
        return value


class PDFScrapeResponse(BaseModel):
    success: bool
    exit_code: int
    output_path: str
    stdout: str = Field("", description="Captured standard output from the scraper process.")
    stderr: str = Field("", description="Captured standard error from the scraper process.")
    duration_seconds: float = Field(..., description="Total runtime of the scraper process in seconds.")


class PDFScrapeJobStatus(str, Enum):
    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class PDFScrapeJobSummary(BaseModel):
    job_id: str
    status: PDFScrapeJobStatus
    created_at: datetime = Field(..., description="UTC timestamp when the job was created.")
    updated_at: datetime = Field(..., description="UTC timestamp when the job status last changed.")


class PDFScrapeJobDetail(PDFScrapeJobSummary):
    request: PDFScrapeRequest
    result: Optional[PDFScrapeResponse] = Field(
        None,
        description="PDF scraper output available after completion.",
    )
    error: Optional[str] = Field(None, description="Error message when the job fails.")
