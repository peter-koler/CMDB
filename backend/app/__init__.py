from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_migrate import Migrate
from config import config

db = SQLAlchemy()
jwt = JWTManager()
migrate = Migrate()
socketio = None


def create_app(config_name="default"):
    global socketio
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    CORS(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})

    # 初始化WebSocket
    from app.notifications.websocket import init_socketio

    socketio = init_socketio(app)

    # JWT error handlers
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({"code": 401, "message": "Token has expired"}), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({"code": 422, "message": "Invalid token"}), 422

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({"code": 401, "message": "Authorization token is missing"}), 401

    @jwt.needs_fresh_token_loader
    def token_not_fresh_callback(jwt_header, jwt_payload):
        return jsonify({"code": 401, "message": "Fresh token required"}), 401

    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        return jsonify({"code": 401, "message": "Token has been revoked"}), 401

    from app.routes import register_routes

    register_routes(app)

    @app.route("/api/v1/health")
    def health_check():
        return {"status": "ok", "message": "IT Ops Platform API"}

    with app.app_context():
        db.create_all()
        init_default_data(app)

    return app


def init_default_data(app):
    from app.models.user import User
    from app.models.config import SystemConfig
    from app.notifications.models import init_default_notification_types
    from app.tasks.scheduler import init_scheduler

    admin = User.query.filter_by(username="admin").first()
    if not admin:
        admin = User(
            username="admin", role="admin", status="active", email="admin@example.com"
        )
        admin.set_password("admin")
        admin.save()

    default_configs = {
        "access_token_expire": "30",
        "refresh_token_expire": "10080",
        "password_min_length": "8",
        "password_force_change_days": "90",
        "password_history_count": "5",
        "max_login_failures": "5",
        "lock_duration_hours": "24",
        "log_retention_days": "30",
        "require_uppercase": "true",
        "require_lowercase": "true",
        "require_digit": "true",
        "require_special": "true",
    }

    for key, value in default_configs.items():
        if not SystemConfig.query.filter_by(config_key=key).first():
            config = SystemConfig(config_key=key, config_value=value)
            db.session.add(config)

    db.session.commit()

    # 初始化默认通知类型
    init_default_notification_types()

    # 初始化调度器
    init_scheduler(app)
