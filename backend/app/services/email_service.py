import os
import threading

import requests

from app.services.email_templates import render_task_created, render_task_completed

BREVO_URL = "https://api.brevo.com/v3/smtp/email"


def send_email(to: str, subject: str, html_body: str) -> None:
    """Send one email through Brevo's HTTPS API (works on Render's free plan)."""
    api_key = os.getenv("BREVO_API_KEY")
    sender = os.getenv("MAIL_SENDER")

    missing = [n for n, v in (("BREVO_API_KEY", api_key), ("MAIL_SENDER", sender)) if not v]
    if missing:
        raise RuntimeError(f"Missing environment variables: {', '.join(missing)}")

    resp = requests.post(
        BREVO_URL,
        headers={
            "api-key": api_key.strip(),
            "accept": "application/json",
            "content-type": "application/json",
        },
        json={
            "sender": {"name": "TaskFlow", "email": sender.strip()},
            "to": [{"email": to}],
            "subject": subject,
            "htmlContent": html_body,
        },
        timeout=15,
    )
    if not resp.ok:
        raise RuntimeError(f"Brevo error {resp.status_code}: {resp.text}")


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