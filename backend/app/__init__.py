from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_migrate import Migrate
from config import config
import os

db = SQLAlchemy()
jwt = JWTManager()
migrate = Migrate()
socketio = None


def create_app(config_name="default"):
    global socketio
    static_folder = os.path.join(os.path.dirname(__file__), "static")
    app = Flask(__name__, static_folder=static_folder, static_url_path="/static")
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
        init_monitoring_templates(app)

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


def init_monitoring_templates(app):
    from app.services.template_service import template_service
    from app.models.monitor_template import MonitorCategory, MonitorTemplate
    
    template_service.initialize()
    
    # 如果数据库中没有分类，则初始化默认分类
    if MonitorCategory.query.count() == 0:
        default_categories = [
            {"name": "数据库", "code": "db", "icon": "database"},
            {"name": "操作系统", "code": "os", "icon": "desktop"},
            {"name": "中间件", "code": "middleware", "icon": "cluster"},
            {"name": "云服务", "code": "cloud", "icon": "cloud"},
            {"name": "网络设备", "code": "network", "icon": "global"},
            {"name": "自定义", "code": "custom", "icon": "code"},
        ]
        for cat in default_categories:
            template_service.save_category(cat["name"], cat["code"], cat["icon"])
    
    # 如果数据库中没有模板，则从 HertzBeat 导入默认模板
    if MonitorTemplate.query.count() == 0:
        import os
        template_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
            'templates'
        )
        if os.path.exists(template_dir):
            for filename in os.listdir(template_dir):
                if filename.endswith('.yml'):
                    filepath = os.path.join(template_dir, filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 从文件名解析 app 名称
                    app_name = filename[4:-4]  # 去掉 "app-" 前缀和 ".yml" 后缀
                    
                    # 简单解析 YAML 获取分类（使用字符串匹配）
                    category = 'custom'
                    name = app_name
                    
                    if 'category:' in content:
                        import re
                        cat_match = re.search(r'category:\s*(\w+)', content)
                        if cat_match:
                            category = cat_match.group(1)
                    
                    if 'zh-CN:' in content:
                        import re
                        name_match = re.search(r'zh-CN:\s*([^\n]+)', content)
                        if name_match:
                            name = name_match.group(1).strip()
                    
                    template_service.save_template(app_name, name, category, content)
    
    print("Monitoring templates initialized successfully!")
