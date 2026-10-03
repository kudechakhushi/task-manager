import re

from flask import Blueprint, redirect, jsonify, request
from werkzeug.security import generate_password_hash, check_password_hash

from app.config import Config
from app.extensions import oauth, supabase
from app.utils.jwt_utils import create_token

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


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

    google_id = info["sub"]
    email = (info.get("email") or "").strip().lower()

    # 1) Find the user by Google id
    found = supabase.table("users").select("*").eq("google_id", google_id).execute()
    if found.data:
        user = found.data[0]
    else:
        # 2) Same email may already exist from a password signup: link the Google account to it
        by_email = supabase.table("users").select("*").eq("email", email).execute()
        if by_email.data:
            user = by_email.data[0]
            supabase.table("users").update(
                {"google_id": google_id, "picture": info.get("picture")}
            ).eq("id", user["id"]).execute()
        else:
            # 3) Brand new user (this is the "sign up")
            created = supabase.table("users").insert({
                "google_id": google_id,
                "email": email,
                "name": info.get("name"),
                "picture": info.get("picture"),
            }).execute()
            user = created.data[0]

    jwt_token = create_token(user["id"])
    return redirect(f"{Config.FRONTEND_URL}/auth/callback?token={jwt_token}")


def validate_registration(name: str, email: str, password: str):
    """Return an error message, or None when everything is valid."""
    if not name:
        return "Full name is required"
    if len(name) < 2:
        return "Name must be at least 2 characters"
    if len(name) > 50:
        return "Name must be 50 characters or fewer"

    if not email:
        return "Email is required"
    if len(email) > 254 or not EMAIL_RE.match(email):
        return "Enter a valid email address"

    if not password:
        return "Password is required"
    if len(password) < 8:
        return "Password must be at least 8 characters"
    if len(password) > 128:
        return "Password must be 128 characters or fewer"
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        return "Password must contain at least one letter and one number"

    return None


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name") or "").strip()
    email = str(data.get("email") or "").strip().lower()
    password = str(data.get("password") or "")

    error = validate_registration(name, email, password)
    if error:
        return jsonify({"error": error}), 400

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
    email = str(data.get("email") or "").strip().lower()
    password = str(data.get("password") or "")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400
    if not EMAIL_RE.match(email):
        return jsonify({"error": "Enter a valid email address"}), 400

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