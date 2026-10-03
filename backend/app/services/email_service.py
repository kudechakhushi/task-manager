import os
import smtplib
import ssl
import threading
from email.message import EmailMessage

from app.services.email_templates import render_task_created, render_task_completed

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465  # SSL


def send_email(to: str, subject: str, html_body: str) -> None:
    """Send one email through Gmail SMTP using an App Password."""
    sender = os.getenv("GMAIL_SENDER")
    password = (os.getenv("GMAIL_APP_PASSWORD") or "").replace(" ", "")

    missing = [n for n, v in (("GMAIL_SENDER", sender), ("GMAIL_APP_PASSWORD", password)) if not v]
    if missing:
        raise RuntimeError(f"Missing environment variables: {', '.join(missing)}")

    msg = EmailMessage()
    msg["To"] = to
    msg["From"] = f"TaskFlow <{sender}>"
    msg["Subject"] = subject
    msg.set_content("Please view this email in an HTML-capable client.")  # plain-text fallback
    msg.add_alternative(html_body, subtype="html")

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context, timeout=20) as server:
        server.login(sender, password)
        server.send_message(msg)


def _send_safe(to: str, subject: str, html_body: str) -> None:
    """An email failure must never break creating or completing a task."""
    try:
        send_email(to, subject, html_body)
        print(f"[email] sent '{subject}' to {to}")
    except Exception as e:
        print(f"[email] FAILED to send to {to}: {e}")


def _send_async(recipients: list[str], subject: str, html_body: str) -> None:
    """Send each email in a background thread so the API responds quickly."""
    for to in recipients:
        threading.Thread(target=_send_safe, args=(to, subject, html_body), daemon=True).start()


def _recipients(*users) -> list[str]:
    """Collect unique email addresses, so one person never gets two copies."""
    seen, out = set(), []
    for u in users:
        email = (u or {}).get("email")
        if email and email not in seen:
            seen.add(email)
            out.append(email)
    return out


def notify_task_created(task: dict, creator: dict, assignee: dict | None) -> None:
    subject, body = render_task_created(task, creator, assignee)
    _send_async(_recipients(creator, assignee), subject, body)


def notify_task_completed(task: dict, completed_by: dict, creator: dict, assignee: dict | None) -> None:
    subject, body = render_task_completed(task, completed_by, creator, assignee)
    _send_async(_recipients(creator, assignee), subject, body)


if __name__ == "__main__":
    # Quick test (run from the backend folder):
    #   python -m app.services.email_service you@gmail.com
    import sys
    from dotenv import load_dotenv

    load_dotenv()
    sample_task = {
        "title": "Test task",
        "description": "Checking that email works",
        "priority": "high",
        "due_date": "2026-10-09",
    }
    person = {"name": "Test User", "email": sys.argv[1]}
    subject, body = render_task_created(sample_task, person, person)
    send_email(sys.argv[1], subject, body)
    print("sent")