from flask import Blueprint, jsonify, g

from app.extensions import supabase
from app.utils.jwt_utils import login_required

users_bp = Blueprint("users", __name__, url_prefix="/api")

@users_bp.get("/me")
@login_required
def me():
    res = supabase.table("users").select("id,name,email,picture").eq("id", g.user_id).execute()
    if not res.data:
        return jsonify({"error": "User not found"}), 404
    return jsonify(res.data[0])

@users_bp.get("/users")
@login_required
def list_users():
    res = supabase.table("users").select("id,name,email,picture").order("name").execute()
    return jsonify(res.data)