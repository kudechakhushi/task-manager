import html
import os
from datetime import datetime

BRAND = "TaskFlow"

PRIORITY_COLORS = {
    "high": ("#fef2f2", "#b91c1c"),
    "medium": ("#fffbeb", "#b45309"),
    "low": ("#ecfdf5", "#047857"),
}


def _e(value) -> str:
    """Escape user text so a task title like <b>hi</b> can't break the email."""
    return html.escape(str(value)) if value not in (None, "") else ""


def _name(user) -> str:
    user = user or {}
    return _e(user.get("name") or user.get("email") or "Unassigned")


def _pretty_date(value) -> str:
    if not value:
        return "No due date"
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").strftime("%d %b %Y")
    except ValueError:
        return _e(value)


def _priority_badge(priority) -> str:
    bg, fg = PRIORITY_COLORS.get(str(priority).lower(), ("#f1f5f9", "#334155"))
    return (
        f'<span style="display:inline-block;background:{bg};color:{fg};padding:2px 10px;'
        f'border-radius:999px;font-size:12px;font-weight:700;text-transform:uppercase">{_e(priority)}</span>'
    )


def _rows_html(rows) -> str:
    return "".join(
        f'<tr>'
        f'<td style="padding:8px 0;width:120px;color:#64748b;font-size:14px;vertical-align:top">{label}</td>'
        f'<td style="padding:8px 0;color:#0f172a;font-size:14px;font-weight:600">{value}</td>'
        f'</tr>'
        for label, value in rows
    )


def _layout(accent: str, tag: str, heading: str, intro: str, task: dict, rows, button_text: str) -> str:
    title = _e(task.get("title"))
    description = _e(task.get("description")) or "No description provided."
    dashboard_url = os.getenv("FRONTEND_URL", "http://localhost:3001").rstrip("/") + "/dashboard"

    return f"""<!doctype html>
<html>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:Arial,Helvetica,sans-serif">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;padding:24px 12px">
    <tr><td align="center">
      <table role="presentation" width="560" cellpadding="0" cellspacing="0"
             style="max-width:560px;width:100%;background:#ffffff;border-radius:12px;overflow:hidden;border:1px solid #e2e8f0">

        <tr><td style="background:{accent};padding:20px 28px">
          <span style="color:#ffffff;font-size:20px;font-weight:700">{BRAND}</span>
          <span style="float:right;color:#ffffff;font-size:12px;font-weight:700;letter-spacing:1px;
                       background:rgba(255,255,255,0.2);padding:4px 10px;border-radius:999px">{tag}</span>
        </td></tr>

        <tr><td style="padding:28px">
          <h1 style="margin:0 0 8px;font-size:22px;color:#0f172a">{heading}</h1>
          <p style="margin:0 0 20px;font-size:14px;color:#475569;line-height:1.5">{intro}</p>

          <div style="border:1px solid #e2e8f0;border-left:4px solid {accent};border-radius:8px;padding:16px;background:#f8fafc">
            <div style="font-size:17px;font-weight:700;color:#0f172a;margin-bottom:6px">{title}</div>
            <div style="font-size:14px;color:#475569;line-height:1.5">{description}</div>
          </div>

          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-top:16px">
            {_rows_html(rows)}
          </table>

          <div style="text-align:center;margin-top:24px">
            <a href="{dashboard_url}"
               style="display:inline-block;background:{accent};color:#ffffff;text-decoration:none;
                      padding:12px 28px;border-radius:8px;font-weight:700;font-size:14px">{button_text}</a>
          </div>
        </td></tr>

        <tr><td style="padding:16px 28px;background:#f8fafc;border-top:1px solid #e2e8f0;
                       font-size:12px;color:#94a3b8;text-align:center">
          You received this email because of activity on a task in {BRAND}.
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""


def render_task_created(task: dict, creator: dict, assignee: dict | None):
    rows = [
        ("Created by", _name(creator)),
        ("Assigned to", _name(assignee)),
        ("Priority", _priority_badge(task.get("priority", "medium"))),
        ("Due date", _pretty_date(task.get("due_date"))),
    ]
    body = _layout(
        accent="#2563eb",
        tag="NEW TASK",
        heading="A new task was created",
        intro=f"{_name(creator)} created a task and assigned it to {_name(assignee)}.",
        task=task,
        rows=rows,
        button_text="Open dashboard",
    )
    return f"New task: {task.get('title')}", body


def render_task_completed(task: dict, completed_by: dict, creator: dict, assignee: dict | None):
    rows = [
        ("Completed by", _name(completed_by)),
        ("Created by", _name(creator)),
        ("Assigned to", _name(assignee)),
        ("Priority", _priority_badge(task.get("priority", "medium"))),
    ]
    body = _layout(
        accent="#059669",
        tag="COMPLETED",
        heading="Task completed ✅",
        intro=f"{_name(completed_by)} marked this task as complete.",
        task=task,
        rows=rows,
        button_text="View tasks",
    )
    return f"Task completed: {task.get('title')}", body


if __name__ == "__main__":
    # Preview without sending any email:  python -m app.services.email_templates
    sample = {
        "title": "Fix the dashboard UI",
        "description": "All design should be upgraded",
        "priority": "high",
        "due_date": "2026-10-09",
    }
    me = {"name": "Khushi Kudecha", "email": "khushi@example.com"}
    other = {"name": "Final Project", "email": "final@example.com"}

    _, created = render_task_created(sample, me, other)
    _, completed = render_task_completed(sample, other, me, other)
    with open("preview_created.html", "w", encoding="utf-8") as f:
        f.write(created)
    with open("preview_completed.html", "w", encoding="utf-8") as f:
        f.write(completed)
    print("Open preview_created.html and preview_completed.html in your browser")