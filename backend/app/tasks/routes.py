from datetime import datetime, timezone

from flask import Blueprint, jsonify, request, g

from app.extensions import supabase
from app.utils.jwt_utils import login_required
from app.services.email_service import send_task_created_email, send_task_completed_email

tasks_bp = Blueprint("tasks", __name__, url_prefix="/api/tasks")

def get_user(user_id):
    if not user_id:
        return None
    res = supabase.table("users").select("id,name,email").eq("id", user_id).execute()
    return res.data[0] if res.data else None

@tasks_bp.post("")
@login_required
def create_task():
    data = request.get_json() or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "Title is required"}), 400

    new_task = {
        "title": title,
        "description": data.get("description"),
        "priority": data.get("priority", "medium"),
        "due_date": data.get("due_date") or None,
        "assigned_to": data.get("assigned_to") or None,
        "created_by": g.user_id,
    }
    task = supabase.table("tasks").insert(new_task).execute().data[0]

    send_task_created_email(task, get_user(g.user_id), get_user(task["assigned_to"]))
    return jsonify(task), 201

@tasks_bp.get("")
@login_required
def list_tasks():
    view = request.args.get("view", "assigned")   # "assigned" or "created"
    column = "created_by" if view == "created" else "assigned_to"
    res = (
        supabase.table("tasks")
        .select("*, creator:users!tasks_created_by_fkey(name,email), "
                "assignee:users!tasks_assigned_to_fkey(name,email)")
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

    updated = supabase.table("tasks").update({
        "status": "completed",
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", task_id).execute().data[0]

    send_task_completed_email(
        updated, get_user(task["created_by"]), get_user(task["assigned_to"]), get_user(g.user_id)
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