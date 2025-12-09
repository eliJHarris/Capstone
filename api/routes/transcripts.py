from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.database import get_db
from dependencies.auth import require_user
from schemas.transcript import TranscriptResponse
from services.transcript_service import TranscriptService

router = APIRouter(prefix="/transcripts", tags=["transcripts"])


@router.get("/me", response_model=TranscriptResponse)
def get_my_transcript(user=Depends(require_user), db: Session = Depends(get_db)):
    return TranscriptService.get_transcript_for_user(db=db, user_claims=user)


@router.get("/{advisee_id}", response_model=TranscriptResponse)
def get_transcript_for_advisee(
    advisee_id: int,
    user=Depends(require_user),
    db: Session = Depends(get_db),
):
    return TranscriptService.get_transcript_for_advisee(
        db=db,
        advisee_id=advisee_id,
        user_claims=user,
    )
