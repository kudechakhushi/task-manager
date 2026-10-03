from flask import Blueprint, redirect, jsonify, request
import re
from werkzeug.security import generate_password_hash, check_password_hash
from app.config import Config
from app.extensions import oauth, supabase
from app.utils.jwt_utils import create_token

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

@auth_bp.get("/google/login")
def google_login():
    redirect_uri = f"{Config.BACKEND_URL}/auth/google/callback"
    return oauth.google.authorize_redirect(redirect_uri)

@auth_bp.get("/google/callback")
def google_callback():
    token = oauth.google.authorize_access_token()
    info = token.get("userinfo")
    if not info:
        return jsonify({"error": "Google login failed"}), 400

    # Find the user by Google id, or create them (this is the "sign up")
    found = supabase.table("users").select("*").eq("google_id", info["sub"]).execute()
    if found.data:
        user = found.data[0]
    else:
        created = supabase.table("users").insert({
            "google_id": info["sub"],
            "email": info["email"],
            "name": info.get("name"),
            "picture": info.get("picture"),
        }).execute()
        user = created.data[0]

    jwt_token = create_token(user["id"])
    return redirect(f"{Config.FRONTEND_URL}/auth/callback?token={jwt_token}")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not name or not email or not password:
        return jsonify({"error": "Name, email and password are required"}), 400
    if not EMAIL_RE.match(email):
        return jsonify({"error": "Enter a valid email address"}), 400
    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400

    existing = supabase.table("users").select("id").eq("email", email).execute()
    if existing.data:
        return jsonify({"error": "An account with this email already exists"}), 409

    supabase.table("users").insert({
        "name": name,
        "email": email,
        "password_hash": generate_password_hash(password),
    }).execute()

    return jsonify({"message": "Account created. Please log in."}), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    res = supabase.table("users").select("id,name,email,password_hash").eq("email", email).execute()
    user = res.data[0] if res.data else None

    if not user:
        return jsonify({"error": "Invalid email or password"}), 401
    if not user.get("password_hash"):
        # Account was created through Google and has no password
        return jsonify({"error": "This account uses Google sign-in. Click 'Continue with Google'."}), 401
    if not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid email or password"}), 401

    token = create_token(user["id"])
    return jsonify({"token": token}), 200