"""
Email tasks (Celery): password reset links.
In dev mode, the reset link is printed to console.
"""
from celery_app import celery_app
from core.config import settings


@celery_app.task(name="tasks.email.send_reset_email")
def send_reset_email(to_email: str, reset_link: str):
    """Send password reset email. Uses SMTP if configured, else prints to console."""
    if not settings.SMTP_USER:
        print(f"[DEV] Password reset link for {to_email}: {reset_link}")
        return

    import smtplib
    from email.mime.text import MIMEText

    body = f"""
Hi,

You requested a password reset for your AI Research Assistant account.

Click the link below (expires in 15 minutes):
{reset_link}

If you did not request this, ignore this email.

— AI Research Assistant
""".strip()

    msg = MIMEText(body)
    msg["Subject"] = "Reset your password"
    msg["From"] = settings.EMAIL_FROM
    msg["To"] = to_email

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(settings.EMAIL_FROM, [to_email], msg.as_string())
