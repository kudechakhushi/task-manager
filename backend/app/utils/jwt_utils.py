import datetime
from functools import wraps

import jwt
from flask import request, jsonify, g

from app.config import Config

def create_token(user_id):
    payload = {
        "user_id": user_id,
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7),
    }
    return jwt.encode(payload, Config.JWT_SECRET, algorithm="HS256")

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return jsonify({"error": "Missing token"}), 401
        token = header.split(" ")[1]
        try:
            data = jwt.decode(token, Config.JWT_SECRET, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401
        g.user_id = data["user_id"]   # available inside the route
        return f(*args, **kwargs)
    return wrapper