from email.message import EmailMessage
import smtplib
from core.config import settings
from pydantic import BaseModel

class EmailData(BaseModel):
    subject: str
    recipient: str
    body: str

def send_email(data):
    msg = EmailMessage()
    msg["From"] = settings.smtp_from
    msg["To"] = data.recipient
    msg["Subject"] = data.subject
    msg.set_content(data.body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
        smtp.starttls()
        smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(msg)
