import asyncio

import resend
from pydantic import BaseModel, EmailStr
from src.util.config import get_settings

class EmailRequest(BaseModel):
    """Request body for sending emails."""
    to: EmailStr
    subject: str
    message: str

class EmailResponse(BaseModel):
    """Response after sending email."""
    success: bool
    id: str

resend.api_key = get_settings().EMAIL_API_KEY

async def send_email(email_request: EmailRequest):
    """Send an email."""
    try:
        result = resend.Emails.send({
            "from": "Nutri Pilot <no-reply@nutripilot.tech>", #os.environ.get("EMAIL_FROM", "Acme <onboarding@resend.dev>"),
            "to": [email_request.to],
            "subject": email_request.subject,
            "html": f"<p>{email_request.message}</p>",
        })
        return EmailResponse(success=True, id=result["id"])
    except Exception as e:
        #raise HTTPException(status_code=500, detail="Failed to send email")
        raise


if __name__ == "__main__":
    asyncio.run(
        send_email(
            EmailRequest(
                to="wangtie0913@gmail.com",
                subject="Test",
                message="This is test"
            )
        )
    )