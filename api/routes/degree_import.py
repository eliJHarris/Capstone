from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.database import get_db
from services.degree_importer import import_degree_plan_from_pdf_url


class DegreeImportPayload(BaseModel):
    pdfUrl: str


router = APIRouter(prefix="/import", tags=["Degree Import"])


@router.post("/pdf/{advisee_id}")
def import_degree_pdf(
    advisee_id: int,
    payload: DegreeImportPayload,
    db: Session = Depends(get_db),
):
    pdf_url = (payload.pdfUrl or "").strip()
    if not pdf_url:
        raise HTTPException(status_code=400, detail="Missing pdfUrl")

    try:
        result = import_degree_plan_from_pdf_url(db, advisee_id, pdf_url)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    validation = result["validation"]
    return {
        "status": "success",
        "data": {
            "requirementSet": result["requirementSet"].requirementSetID,
            "contextID": result["context"].contextID,
            "validation": {
                "status": validation.status.name,
                "completion": float(validation.completionPercent or 0),
                "issues": validation.issues or [],
            },
        },
    }
