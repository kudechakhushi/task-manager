import base64
import threading
from email.mime.text import MIMEText

import requests
from markupsafe import escape

from app.config import Config

def _get_access_token():
    # Exchange the long-lived refresh token for a short-lived access token
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": Config.GOOGLE_CLIENT_ID,
        "client_secret": Config.GOOGLE_CLIENT_SECRET,
        "refresh_token": Config.GMAIL_REFRESH_TOKEN,
        "grant_type": "refresh_token",
    }, timeout=10)
    r.raise_for_status()
    return r.json()["access_token"]

def _send(recipients, subject, html):
    recipients = list({r for r in recipients if r})
    if not recipients:
        return

    def worker():
        try:
            msg = MIMEText(html, "html")
            msg["to"] = ", ".join(recipients)
            msg["from"] = Config.GMAIL_SENDER
            msg["subject"] = subject
            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
            requests.post(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
                headers={"Authorization": f"Bearer {_get_access_token()}"},
                json={"raw": raw},
                timeout=10,
            ).raise_for_status()
        except Exception as e:
            print("Email failed:", e)   # a failed email must not break the API

    threading.Thread(target=worker, daemon=True).start()

def _name(user):
    return user.get("name") or user["email"] if user else "Unassigned"

def send_task_created_email(task, creator, assignee):
    recipients = [creator["email"]] + ([assignee["email"]] if assignee else [])
    html = f"""
      <h2>New task: {escape(task['title'])}</h2>
      <p>{escape(task.get('description') or '')}</p>
      <p><b>Created by:</b> {escape(_name(creator))}<br>
         <b>Assigned to:</b> {escape(_name(assignee))}<br>
         <b>Priority:</b> {task['priority']}<br>
         <b>Due:</b> {task.get('due_date') or 'Not set'}</p>"""
    _send(recipients, f"New task: {task['title']}", html)

def send_task_completed_email(task, creator, assignee, completed_by):
    recipients = [creator["email"]] + ([assignee["email"]] if assignee else [])
    html = f"""
      <h2>Task completed: {escape(task['title'])}</h2>
      <p>Marked complete by <b>{escape(_name(completed_by))}</b>.</p>"""
    _send(recipients, f"Task completed: {task['title']}", html)