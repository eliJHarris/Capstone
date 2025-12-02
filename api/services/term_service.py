from typing import List, Optional

from sqlalchemy.orm import Session

from models.schedule import Term
from schemas.term import TermResponse


class TermService:
    """Service helpers for working with academic terms."""

    @staticmethod
    def list_terms(
        db: Session,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[TermResponse]:
        query = db.query(Term)

        if search:
            query = query.filter(Term.code.ilike(f"%{search}%"))

        terms = (
            query.order_by(Term.startDate.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        return [
            TermResponse(
                termID=term.termID,
                code=term.code,
                startDate=term.startDate,
                endDate=term.endDate,
            )
            for term in terms
        ]
