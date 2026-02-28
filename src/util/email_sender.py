
import smtplib

from src.util.logger import get_logger
from src.util.config import get_settings
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
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

        logo = MIMEImage(open('static/email/favicon.png', 'rb').read())
        logo.add_header('Content-ID', '<logo>')
        msg.attach(logo)

        msg.attach(MIMEText(body, "html"))

        server = smtplib.SMTP(conf.SMTP_HOST, conf.SMTP_PORT, timeout=10)
        server.starttls()

        server.login(conf.SMTP_USER, conf.SMTP_PASSWORD)

        result = server.sendmail(conf.SMTP_FROM, to_email, msg.as_string())
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
    res = send_email("wangtie0913@gmail.com", "Registration OTP", "<h1>Hello This is your OTP : 123456</h1>")
    print(res)