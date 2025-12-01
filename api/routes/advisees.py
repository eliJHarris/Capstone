from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db.database import get_db
from schemas.advisee import AdviseeListItem
from services.advisee_service import AdviseeService

router = APIRouter(prefix="/advisees", tags=["advisees"])


def _list_advisees(
  advisor_id: Optional[int] = Query(None, description="Filter by advisor ID"),
  search: Optional[str] = Query(None, description="Search by name, email, or major"),
  skip: int = Query(0, ge=0, description="Records to skip"),
  limit: int = Query(50, ge=1, le=200, description="Maximum records to return"),
  db: Session = Depends(get_db),
):
  return AdviseeService.list_advisees(
    db=db,
    advisor_id=advisor_id,
    search=search,
    skip=skip,
    limit=limit,
  )


@router.get("/", response_model=List[AdviseeListItem])
def list_advisees_with_slash(
  advisor_id: Optional[int] = Query(None, description="Filter by advisor ID"),
  search: Optional[str] = Query(None, description="Search by name, email, or major"),
  skip: int = Query(0, ge=0, description="Records to skip"),
  limit: int = Query(50, ge=1, le=200, description="Maximum records to return"),
  db: Session = Depends(get_db),
):
  return _list_advisees(advisor_id, search, skip, limit, db)


@router.get("", response_model=List[AdviseeListItem], include_in_schema=False)
def list_advisees_no_slash(
  advisor_id: Optional[int] = Query(None, description="Filter by advisor ID"),
  search: Optional[str] = Query(None, description="Search by name, email, or major"),
  skip: int = Query(0, ge=0, description="Records to skip"),
  limit: int = Query(50, ge=1, le=200, description="Maximum records to return"),
  db: Session = Depends(get_db),
):
  return _list_advisees(advisor_id, search, skip, limit, db)
