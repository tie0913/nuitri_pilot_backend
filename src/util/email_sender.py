
import smtplib

from .logger import get_logger
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

EMAIL_ADDRESS = "nuitripilot@gmail.com"
EMAIL_PASSWORD = "jeic myvu opql afef"

#
# sending email util code
#
def send_email(to_email: str, subject: str, body: str) -> bool:

    feedback = False
    logger = get_logger("send_email")
    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10)
        server.starttls()

        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)

        result = server.sendmail(EMAIL_ADDRESS, to_email, msg.as_string())
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
    res = send_email("wang9431@saskpolytech.ca", "测试邮件", "你好，这是一封来自 Python 的测试邮件！")
    print(res)