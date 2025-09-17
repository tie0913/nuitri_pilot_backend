
import smtplib

from .logger import get_logger
from .config import get_settings
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

#
# sending email util code
#
def send_email(to_email: str, subject: str, body: str) -> bool:
    conf = get_settings()
    feedback = False
    logger = get_logger("send_email")
    try:
        msg = MIMEMultipart()
        msg["From"] = conf.SMTP_FROM
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP(conf.SMTP_HOST, conf.SMTP_PORT, timeout=10)
        server.starttls()

        server.login(conf.EMAIL_ADDRESS, conf.EMAIL_PASSWORD)

        result = server.sendmail(conf.EMAIL_ADDRESS, to_email, msg.as_string())
        server.quit()

        if not result:
            feedback = True
            logger.info(f"sending email has succeeded")
        else:
            logger.error(f"sending email occurs error: {result}")

    except smtplib.SMTPException as e:
        logger.error(f"sending email occurs SMTP error: {e}")
    except Exception as e:
        logger.error(f"sending email occurs error: {e}")
    
    return feedback


if __name__ == "__main__":
    res = send_email("wang9431@saskpolytech.ca", "Test Email", "Hello, this is an email coming from Nuitri Pilot")
    print(res)