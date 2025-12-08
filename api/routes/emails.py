from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from db.database import get_db
from routes.users import get_user
from services.email_service import send_email, EmailData

router = APIRouter(
    prefix="/emails",
    tags=["emails"]
)

@router.post("/notify")
async def notify_user(user_id: int, background: BackgroundTasks, db=Depends(get_db)):
    user = get_user(user_id, db)
    msg = f"Hi {user.username}, you have a new notification."

    background.add_task(send_email, EmailData(
        subject="New Notification",
        recipient=user.email,
        body=f"<p>{msg}</p>",
    ))

    return {"status": "queued"}
