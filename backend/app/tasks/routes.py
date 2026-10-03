from datetime import date, datetime, timezone

from flask import Blueprint, jsonify, request, g

from app.extensions import supabase
from app.services.email_service import notify_task_created, notify_task_completed
from app.utils.jwt_utils import login_required

tasks_bp = Blueprint("tasks", __name__, url_prefix="/api/tasks")

VALID_PRIORITIES = {"low", "medium", "high"}


def get_user(user_id):
    """Fetch one user's id, name and email (used to address the notification emails)."""
    if not user_id:
        return None
    res = supabase.table("users").select("id,name,email").eq("id", user_id).execute()
    return res.data[0] if res.data else None


def validate_task_input(data: dict):
    """Return (clean_values, error_message). error_message is None when everything is valid."""
    title = data.get("title")
    if not isinstance(title, str) or not title.strip():
        return None, "Task title is required"
    title = title.strip()
    if len(title) < 3 or len(title) > 100:
        return None, "Title must be between 3 and 100 characters"

    description = data.get("description") or ""
    if not isinstance(description, str):
        return None, "Description must be text"
    description = description.strip()
    if len(description) > 500:
        return None, "Description must be 500 characters or fewer"

    priority = data.get("priority") or "medium"
    if priority not in VALID_PRIORITIES:
        return None, "Priority must be low, medium or high"

    due_date = data.get("due_date") or None
    if due_date:
        try:
            parsed = date.fromisoformat(str(due_date))
        except ValueError:
            return None, "Due date must be a valid date (YYYY-MM-DD)"
        if parsed < date.today():
            return None, "Due date cannot be in the past"
        due_date = parsed.isoformat()

    assigned_to = data.get("assigned_to") or None
    if assigned_to and not get_user(assigned_to):
        return None, "The selected assignee does not exist"

    return {
        "title": title,
        "description": description or None,
        "priority": priority,
        "due_date": due_date,
        "assigned_to": assigned_to,
    }, None


@tasks_bp.post("")
@login_required
def create_task():
    data = request.get_json(silent=True) or {}
    clean, error = validate_task_input(data)
    if error:
        return jsonify({"error": error}), 400

    new_task = {**clean, "created_by": g.user_id}
    task = supabase.table("tasks").insert(new_task).execute().data[0]

    # Email the creator and the assignee (runs in a background thread).
    notify_task_created(
        task,
        get_user(g.user_id),
        get_user(task.get("assigned_to")),
    )
    return jsonify(task), 201


@tasks_bp.get("")
@login_required
def list_tasks():
    view = request.args.get("view", "assigned")  # "assigned" or "created"
    if view not in ("assigned", "created"):
        return jsonify({"error": "view must be 'assigned' or 'created'"}), 400
    column = "created_by" if view == "created" else "assigned_to"
    res = (
        supabase.table("tasks")
        .select(
            "*, creator:users!tasks_created_by_fkey(name,email), "
            "assignee:users!tasks_assigned_to_fkey(name,email)"
        )
        .eq(column, g.user_id)
        .order("created_at", desc=True)
        .execute()
    )
    return jsonify(res.data)


@tasks_bp.patch("/<task_id>/complete")
@login_required
def complete_task(task_id):
    res = supabase.table("tasks").select("*").eq("id", task_id).execute()
    if not res.data:
        return jsonify({"error": "Task not found"}), 404
    task = res.data[0]

    if g.user_id not in (task["created_by"], task["assigned_to"]):
        return jsonify({"error": "Not allowed"}), 403
    if task["status"] == "completed":
        return jsonify(task)

    updated = (
        supabase.table("tasks")
        .update(
            {
                "status": "completed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        .eq("id", task_id)
        .execute()
        .data[0]
    )

    # Argument order: task, who completed it, creator, assignee
    notify_task_completed(
        updated,
        get_user(g.user_id),
        get_user(task["created_by"]),
        get_user(task.get("assigned_to")),
    )
    return jsonify(updated)


@tasks_bp.delete("/<task_id>")
@login_required
def delete_task(task_id):
    res = supabase.table("tasks").select("created_by").eq("id", task_id).execute()
    if not res.data:
        return jsonify({"error": "Task not found"}), 404
    if res.data[0]["created_by"] != g.user_id:
        return jsonify({"error": "Only the creator can delete"}), 403
    supabase.table("tasks").delete().eq("id", task_id).execute()
    return jsonify({"message": "Deleted"})