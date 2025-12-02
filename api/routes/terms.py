from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from dependencies.auth import require_user
from db.database import get_db
from schemas.term import TermResponse
from services.term_service import TermService

router = APIRouter(prefix="/terms", tags=["terms"])


def _list_terms(
    search: Optional[str] = Query(None, description="Search by term code or name"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of records to return"),
    user=Depends(require_user),
    db: Session = Depends(get_db),
):
    return TermService.list_terms(
        db=db,
        search=search,
        skip=skip,
        limit=limit,
    )


@router.get("/", response_model=List[TermResponse])
def list_terms_with_slash(
    search: Optional[str] = Query(None, description="Search by term code or name"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of records to return"),
    user=Depends(require_user),
    db: Session = Depends(get_db),
):
    return _list_terms(search, skip, limit, user, db)


@router.get("", response_model=List[TermResponse], include_in_schema=False)
def list_terms_no_slash(
    search: Optional[str] = Query(None, description="Search by term code or name"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of records to return"),
    user=Depends(require_user),
    db: Session = Depends(get_db),
):
    return _list_terms(search, skip, limit, user, db)
