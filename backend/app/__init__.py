from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
from app.config import Config
from app.extensions import oauth

def create_app():
    app = Flask(__name__)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    app.secret_key = Config.SECRET_KEY            # needed for OAuth state in the session
    CORS(app, origins=[Config.FRONTEND_URL])      # only our frontend may call the API

    oauth.init_app(app)
    oauth.register(
        name="google",
        client_id=Config.GOOGLE_CLIENT_ID,
        client_secret=Config.GOOGLE_CLIENT_SECRET,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )

    from app.auth.routes import auth_bp
    from app.users.routes import users_bp
    from app.tasks.routes import tasks_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(tasks_bp)

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    return app