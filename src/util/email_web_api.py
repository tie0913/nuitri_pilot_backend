import asyncio
import httpx
from src.util.config import get_settings

SENDGRID_API_KEY = get_settings().SMTP_WEB_API_KEY

async def send_email(to_email: str, subject: str, content: str):
    url = "https://api.sendgrid.com/v3/mail/send"

    print(SENDGRID_API_KEY)
    headers = {
        "Authorization": f"Bearer {SENDGRID_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "personalizations": [
            {
                "to": [{"email": to_email}]
            }
        ],
        "from": {"email": "no-reply@nutripilot.tech"},
        "subject": subject,
        "content": [
            {
                "type": "text/html",
                "value": content
            }
        ]
    }

    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.post(url, headers=headers, json=data)

    if response.status_code != 202:
        raise Exception(f"SendGrid error: {response.status_code}, {response.text}")

    return True

if __name__ == "__main__":

    asyncio.run(send_email("wangtie0913@gmail.com", "test", "<h2>Test Code</h2>"))