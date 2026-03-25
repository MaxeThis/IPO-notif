"""
Sends HTML emails via SMTP (works with Gmail App Passwords out of the box).
"""
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

log = logging.getLogger(__name__)


def send_email(subject: str, html_body: str) -> bool:
    """
    Send an HTML email. Returns True on success.

    Reads config from environment variables:
        EMAIL_SENDER    — from address (e.g. you@gmail.com)
        EMAIL_PASSWORD  — SMTP password / Gmail App Password
        EMAIL_RECIPIENT — to address
        SMTP_HOST       — default smtp.gmail.com
        SMTP_PORT       — default 587
    """
    sender = os.environ["EMAIL_SENDER"]
    password = os.environ["EMAIL_PASSWORD"]
    recipient = os.environ["EMAIL_RECIPIENT"]
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"IPO Notifier <{sender}>"
    msg["To"] = recipient

    # Plain-text fallback (strip HTML tags roughly)
    import re
    plain = re.sub(r"<[^>]+>", "", html_body).strip()
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.login(sender, password)
            server.sendmail(sender, [recipient], msg.as_string())
        log.info("Email sent: %s", subject)
        return True
    except Exception as exc:
        log.error("Failed to send email: %s", exc)
        return False
